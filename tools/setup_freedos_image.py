#!/usr/bin/env python3
"""Create the local FreeDOS disk image used by QEMU compatibility runs."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

from project_paths import DEFAULT_FREEDOS_IMAGE, game_dir
from qemu_snapshot import mtools_image
from setup_vgabios import build_patched_vgabios


FREEDOS_LITEUSB_URL = (
    "https://www.ibiblio.org/pub/micro/pc-stuff/freedos/files/"
    "distributions/1.4/FD14-LiteUSB.zip"
)
FREEDOS_LITEUSB_SHA256 = "857dcd2ebf9d3d094320154db5fb5b830acba6fb98f981a95a0ca7ab3350338b"
DEFAULT_CACHE_DIR = Path("build/downloads")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_file(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output)


def image_members(zip_path: Path) -> list[zipfile.ZipInfo]:
    with zipfile.ZipFile(zip_path) as archive:
        return sorted(
            (
                info
                for info in archive.infolist()
                if not info.is_dir() and info.filename.lower().endswith(".img")
            ),
            key=lambda info: info.file_size,
            reverse=True,
        )


def extract_largest_image(zip_path: Path, output: Path, force: bool) -> str:
    members = image_members(zip_path)
    if not members:
        raise SystemExit(f"no .img member found in {zip_path}")
    if output.exists() and not force:
        raise SystemExit(f"{output} already exists; pass --force to replace it")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    if temporary.exists():
        temporary.unlink()
    selected = members[0]
    with zipfile.ZipFile(zip_path) as archive, archive.open(selected) as source, temporary.open("wb") as target:
        shutil.copyfileobj(source, target)
    temporary.replace(output)
    return selected.filename


def require_tool(name: str) -> None:
    if shutil.which(name) is None:
        raise SystemExit(f"required tool not found on PATH: {name}")


def run_mtools(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=True, capture_output=True, text=True)


def write_dos_text(image: str, dos_path: str, text: str) -> None:
    with tempfile.NamedTemporaryFile("w", encoding="ascii", newline="\r\n", delete=False) as handle:
        host_path = Path(handle.name)
        handle.write(text)
    try:
        run_mtools(["mcopy", "-o", "-i", image, str(host_path), f"::{dos_path}"])
    finally:
        host_path.unlink(missing_ok=True)


def patch_prompt_boot(image: str) -> None:
    autoexec = """@ECHO OFF
SET DOSDIR=C:\\FDOS
SET PATH=C:\\FDOS\\BIN;C:\\
PROMPT $P$G
CD \\
"""
    write_dos_text(image, "/AUTOEXEC.BAT", autoexec)
    write_dos_text(image, "/FDAUTO.BAT", autoexec)


def make_dos_dir(image: str, dos_path: str) -> None:
    created = subprocess.run(
        ["mmd", "-i", image, f"::{dos_path}"],
        check=False,
        capture_output=True,
        text=True,
    )
    output = (created.stdout + created.stderr).lower()
    if created.returncode != 0 and "already exists" not in output:
        raise SystemExit(created.stdout + created.stderr)


def copy_game_files(image: str, source: Path, dos_dir: str) -> None:
    if not source.is_dir():
        raise SystemExit(f"game directory does not exist: {source}")
    make_dos_dir(image, f"/{dos_dir}")
    files = [path for path in sorted(source.iterdir()) if path.is_file()]
    if not files:
        raise SystemExit(f"game directory has no files: {source}")
    run_mtools(["mcopy", "-o", "-i", image, *(str(path) for path in files), f"::/{dos_dir}"])


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Download the FreeDOS 1.4 LiteUSB image, verify it, extract the raw "
            "disk image, and optionally copy one local AGI game directory onto it."
        )
    )
    parser.add_argument("--url", default=FREEDOS_LITEUSB_URL)
    parser.add_argument("--sha256", default=FREEDOS_LITEUSB_SHA256)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_FREEDOS_IMAGE)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--copy-game", action="store_true")
    parser.add_argument("--game-dir", type=Path)
    parser.add_argument("--dos-game-dir", default="GAME")
    parser.add_argument("--no-prompt-patch", action="store_true")
    parser.add_argument(
        "--skip-vgabios",
        action="store_true",
        help="do not build/verify the QEMU INT-43h-compatible VGA option ROM",
    )
    parser.add_argument("--print-mtools-image", action="store_true")
    args = parser.parse_args()

    if args.print_mtools_image and args.output.exists() and not args.force and not args.copy_game:
        print(mtools_image(args.output))
        return 0

    require_tool("mcopy")
    require_tool("mmd")

    if not args.skip_vgabios:
        vgabios, built = build_patched_vgabios(force=args.force)
        print(f"VGA BIOS: {vgabios} ({'rebuilt' if built else 'verified'})")

    zip_path = args.cache_dir / Path(urllib.parse.urlparse(args.url).path).name
    if not zip_path.exists():
        print(f"downloading: {args.url}")
        download_file(args.url, zip_path)

    actual_sha = sha256_file(zip_path)
    if actual_sha.lower() != args.sha256.lower():
        raise SystemExit(f"sha256 mismatch for {zip_path}: expected {args.sha256}, got {actual_sha}")

    member = extract_largest_image(zip_path, args.output, args.force)
    image = mtools_image(args.output)

    if not args.no_prompt_patch:
        patch_prompt_boot(image)

    if args.copy_game:
        copy_game_files(image, args.game_dir or game_dir(), args.dos_game_dir)

    print(f"zip: {zip_path}")
    print(f"extracted: {member}")
    print(f"image: {args.output}")
    print(f"mtools image: {image}")
    if args.copy_game:
        print(f"copied game to: C:\\{args.dos_game_dir}")
    if args.print_mtools_image:
        print(image)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
