#!/usr/bin/env python3
"""Read-only census for local AGI game/resource directories."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from agi_resources import (
    KIND_ORDER,
    detect_layout,
    iter_present_entries,
    read_directory_entries,
    read_volume_record,
)


VERSION_RE = re.compile(rb"Version[ \t]+[0-9][0-9A-Za-z_.-]*")
VERSION_SOURCE_NAMES = ("AGIDATA.OVL", "AGI", "SIERRA.COM")


def _child_case_insensitive(directory: Path, name: str) -> Path | None:
    candidate = directory / name
    if candidate.exists():
        return candidate
    wanted = name.upper()
    for child in directory.iterdir():
        if child.name.upper() == wanted:
            return child
    return None


def extract_version_strings(game_dir: Path) -> list[str]:
    """Return unique local version strings found in known interpreter files."""

    versions: list[str] = []
    seen: set[str] = set()
    for name in VERSION_SOURCE_NAMES:
        path = _child_case_insensitive(game_dir, name)
        if path is None or not path.is_file():
            continue
        data = path.read_bytes()
        for match in VERSION_RE.finditer(data):
            version = match.group(0).decode("ascii", errors="ignore").strip()
            if version and version not in seen:
                seen.add(version)
                versions.append(version)
    return versions


def _volume_files(game_dir: Path, prefix: str, max_volume: int = 15) -> list[str]:
    names: list[str] = []
    for volume in range(max_volume + 1):
        expected = f"{prefix}VOL.{volume}" if prefix else f"VOL.{volume}"
        path = _child_case_insensitive(game_dir, expected)
        if path is not None and path.is_file():
            names.append(path.name)
    return names


def census_game(game_dir: Path) -> dict[str, Any]:
    """Return a read-only resource census for one local game directory."""

    game_dir = Path(game_dir)
    result: dict[str, Any] = {
        "path": str(game_dir),
        "name": game_dir.name,
        "versions": extract_version_strings(game_dir),
    }

    try:
        layout = detect_layout(game_dir)
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result

    result["layout"] = layout.version
    result["prefix"] = layout.prefix
    result["volume_files"] = _volume_files(game_dir, layout.prefix)
    if layout.section_offsets is not None:
        result["section_offsets"] = {
            kind: f"0x{offset:04x}" for kind, offset in layout.section_offsets.items()
        }

    resources: dict[str, Any] = {}
    total_transform_counts: dict[str, int] = {}
    total_record_errors: list[str] = []
    for kind in KIND_ORDER:
        try:
            entries = read_directory_entries(game_dir, kind)
        except Exception as exc:
            resources[kind] = {
                "error": f"{type(exc).__name__}: {exc}",
            }
            continue

        present = [(number, entry) for number, entry in iter_present_entries(game_dir, kind)]
        volumes = sorted({entry.volume for _, entry in present})
        transform_counts: dict[str, int] = {}
        stored_bytes = 0
        expanded_bytes = 0
        record_errors: list[str] = []

        for number, _entry in present:
            try:
                record = read_volume_record(game_dir, kind, number)
            except Exception as exc:
                record_errors.append(f"{kind} {number}: {type(exc).__name__}: {exc}")
                continue
            transform_counts[record.transform] = transform_counts.get(record.transform, 0) + 1
            total_transform_counts[record.transform] = total_transform_counts.get(record.transform, 0) + 1
            stored_bytes += record.stored_length
            expanded_bytes += record.expanded_length

        if record_errors:
            total_record_errors.extend(record_errors)
        resources[kind] = {
            "entries": len(entries),
            "present": len(present),
            "volumes": volumes,
            "transform_counts": transform_counts,
            "stored_bytes": stored_bytes,
            "expanded_bytes": expanded_bytes,
            "record_errors": record_errors,
        }

    result["resources"] = resources
    result["transform_counts"] = total_transform_counts
    result["record_errors"] = total_record_errors
    return result


def discover_game_dirs(games_root: Path) -> list[Path]:
    """Return first-level child directories under an explicit games root."""

    games_root = Path(games_root)
    return sorted(path for path in games_root.iterdir() if path.is_dir())


def build_census(game_dirs: list[Path], games_root: Path | None = None) -> dict[str, Any]:
    inputs = list(game_dirs)
    if games_root is not None:
        inputs.extend(discover_game_dirs(games_root))
    if not inputs:
        raise SystemExit("error: pass at least one --game-dir PATH or --games-root PATH")

    unique: list[Path] = []
    seen: set[Path] = set()
    for path in inputs:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(path)

    return {
        "games": [census_game(path) for path in unique],
    }


def _resource_row(game: dict[str, Any]) -> str:
    if "resources" not in game:
        return game.get("error", "")
    parts: list[str] = []
    for kind in KIND_ORDER:
        summary = game["resources"].get(kind, {})
        if "error" in summary:
            parts.append(f"{kind}: error")
        else:
            parts.append(f"{kind}: {summary['present']}/{summary['entries']}")
    return "; ".join(parts)


def format_markdown(census: dict[str, Any]) -> str:
    lines = [
        "# Local game census",
        "",
        "Generated from explicit local game directories. Game files remain private inputs.",
        "",
        "| Game | Version strings | Layout | Prefix | Volumes | Resources | Record errors |",
        "| --- | --- | --- | --- | --- | --- | ---: |",
    ]
    for game in census["games"]:
        versions = ", ".join(game.get("versions") or [""])
        layout = game.get("layout", game.get("error", ""))
        prefix = game.get("prefix", "")
        volumes = ", ".join(game.get("volume_files", []))
        errors = len(game.get("record_errors", []))
        lines.append(
            f"| `{game['name']}` | {versions} | {layout} | `{prefix}` | "
            f"{volumes} | {_resource_row(game)} | {errors} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_output(path: Path | None, text: str) -> None:
    if path is None:
        print(text, end="")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="ascii")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-dir", action="append", type=Path, default=[], help="local game directory to inspect")
    parser.add_argument("--games-root", type=Path, help="scan first-level child directories under this explicit root")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--output", type=Path, help="write the report to this path instead of stdout")
    args = parser.parse_args()

    census = build_census(args.game_dir, args.games_root)
    if args.format == "markdown":
        write_output(args.output, format_markdown(census))
    else:
        text = json.dumps(census, indent=2, sort_keys=True) + "\n"
        write_output(args.output, text)


if __name__ == "__main__":
    main()
