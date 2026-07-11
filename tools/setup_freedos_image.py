#!/usr/bin/env python3
"""Create the local FreeDOS disk image used by QEMU compatibility runs."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import struct
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
DEFAULT_IMAGE_SIZE_MIB = 1024
SECTOR_SIZE = 512
PARTITION_START_LBA = 2048
PARTITION_TYPE_FAT16_LBA = 0x0E
DISK_HEADS = 32
DISK_SECTORS_PER_TRACK = 63
FAT16_SECTORS_PER_CLUSTER = 64


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_file(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".download")
    temporary.unlink(missing_ok=True)
    try:
        with urllib.request.urlopen(url) as response, temporary.open("wb") as output:
            shutil.copyfileobj(response, output)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


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


def chs_address(lba: int) -> bytes:
    """Encode an LBA as an MBR CHS triplet for the declared disk geometry."""
    cylinder, remainder = divmod(lba, DISK_HEADS * DISK_SECTORS_PER_TRACK)
    head, sector_index = divmod(remainder, DISK_SECTORS_PER_TRACK)
    sector = sector_index + 1
    if cylinder > 1023:
        return b"\xfe\xff\xff"
    return bytes((head, sector | ((cylinder >> 2) & 0xC0), cylinder & 0xFF))


def partitioned_mbr(source_mbr: bytes, image_size: int) -> bytes:
    """Return the source MBR boot code with one active full-size FAT16 partition."""
    if len(source_mbr) != SECTOR_SIZE or source_mbr[510:512] != b"\x55\xaa":
        raise SystemExit("FreeDOS source image has no valid MBR boot sector")
    if image_size % SECTOR_SIZE:
        raise SystemExit("image size must be a multiple of 512 bytes")
    total_sectors = image_size // SECTOR_SIZE
    partition_sectors = total_sectors - PARTITION_START_LBA
    if partition_sectors <= 0:
        raise SystemExit("image is too small for the configured partition offset")

    result = bytearray(source_mbr)
    result[446:510] = b"\x00" * 64
    entry = (
        b"\x80"
        + chs_address(PARTITION_START_LBA)
        + bytes((PARTITION_TYPE_FAT16_LBA,))
        + chs_address(total_sectors - 1)
        + struct.pack("<II", PARTITION_START_LBA, partition_sectors)
    )
    result[446:462] = entry
    return bytes(result)


def copy_volume_tree(source_image: str, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    run_mtools(["mcopy", "-s", "-i", source_image, "::/*", str(destination)])


def format_large_freedos_image(source_image: Path, output: Path, image_size: int) -> None:
    """Create a bootable enlarged FAT16 disk and copy the source volume into it."""
    source_offset = int(mtools_image(source_image).rsplit("@@", 1)[-1])
    source_bytes = source_image.read_bytes()
    source_mbr = source_bytes[:SECTOR_SIZE]
    source_boot = source_bytes[source_offset : source_offset + SECTOR_SIZE]
    if len(source_boot) != SECTOR_SIZE or source_boot[510:512] != b"\x55\xaa":
        raise SystemExit("FreeDOS source partition has no valid boot sector")

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix="freedos-volume-") as temp_dir:
        contents = Path(temp_dir) / "contents"
        boot_sector = Path(temp_dir) / "boot-sector.bin"
        boot_sector.write_bytes(source_boot)
        copy_volume_tree(mtools_image(source_image), contents)

        try:
            with temporary.open("wb") as target:
                target.truncate(image_size)
                target.seek(0)
                target.write(partitioned_mbr(source_mbr, image_size))

            partition_offset = PARTITION_START_LBA * SECTOR_SIZE
            target_image = f"{temporary}@@{partition_offset}"
            run_mtools(
                [
                    "mformat",
                    "-i",
                    target_image,
                    "-B",
                    str(boot_sector),
                    "-v",
                    "FD14-LITE",
                    "-H",
                    str(PARTITION_START_LBA),
                    "-h",
                    str(DISK_HEADS),
                    "-n",
                    str(DISK_SECTORS_PER_TRACK),
                    "-c",
                    str(FAT16_SECTORS_PER_CLUSTER),
                    "::",
                ]
            )
            members = sorted(contents.iterdir())
            if not members:
                raise SystemExit("FreeDOS source volume is empty")
            run_mtools(["mcopy", "-s", "-o", "-i", target_image, *(str(path) for path in members), "::/"])
            temporary.replace(output)
        finally:
            temporary.unlink(missing_ok=True)


def build_freedos_image(zip_path: Path, output: Path, force: bool, image_size: int) -> str:
    if output.exists() and not force:
        raise SystemExit(f"{output} already exists; pass --force to replace it")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="freedos-source-") as temp_dir:
        source_image = Path(temp_dir) / "source.img"
        member = extract_largest_image(zip_path, source_image, force=True)
        format_large_freedos_image(source_image, output, image_size)
    return member


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
    parser.add_argument(
        "--image-size-mib",
        type=int,
        default=DEFAULT_IMAGE_SIZE_MIB,
        help="raw disk size in MiB (default: 1024)",
    )
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
    require_tool("mformat")

    if not 64 <= args.image_size_mib <= 2048:
        raise SystemExit("--image-size-mib must be between 64 and 2048 for FAT16")

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

    image_size = args.image_size_mib * 1024 * 1024
    member = build_freedos_image(zip_path, args.output, args.force, image_size)
    image = mtools_image(args.output)

    if not args.no_prompt_patch:
        patch_prompt_boot(image)

    if args.copy_game:
        copy_game_files(image, args.game_dir or game_dir(), args.dos_game_dir)

    print(f"zip: {zip_path}")
    print(f"extracted: {member}")
    print(f"image: {args.output}")
    print(f"image size: {args.image_size_mib} MiB")
    print(f"mtools image: {image}")
    if args.copy_game:
        print(f"copied game to: C:\\{args.dos_game_dir}")
    if args.print_mtools_image:
        print(image)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
