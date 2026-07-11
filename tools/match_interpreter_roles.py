#!/usr/bin/env python3
"""Match symbolic interpreter roles across explicit local executable images."""

from __future__ import annotations

import argparse
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from compare_gr_sq2_static import SUBSYSTEM_PAIRS, normalized_snippet
from compare_interpreter_tables import load_build


TARGET_RE = re.compile(
    r"\b(?:call|jmp|j[a-z]+)\s+(?:word\s+|near\s+)?0x([0-9a-f]+)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class RoleMatch:
    label: str
    reference_address: int
    target_addresses: tuple[int, ...]


def parse_role(text: str) -> tuple[str, int]:
    try:
        label, address = text.split("=", 1)
        return label, int(address, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("role must be LABEL=ADDRESS") from exc


def candidate_addresses(
    image: bytes,
    *,
    table_handlers: tuple[int, ...] = (),
    additional: tuple[int, ...] = (),
) -> tuple[int, ...]:
    result = subprocess.run(
        ["ndisasm", "-b", "16", "-o", "0", "-"],
        input=image,
        check=True,
        stdout=subprocess.PIPE,
    )
    candidates = set(table_handlers)
    candidates.update(additional)
    for line in result.stdout.decode("ascii", errors="replace").splitlines():
        match = TARGET_RE.search(line)
        if match is None:
            continue
        address = int(match.group(1), 16)
        if 0 <= address < len(image):
            candidates.add(address)
    return tuple(sorted(address for address in candidates if 0 <= address < len(image)))


def match_roles(
    reference_image: bytes,
    target_image: bytes,
    roles: tuple[tuple[str, int], ...],
    target_candidates: tuple[int, ...],
) -> tuple[RoleMatch, ...]:
    target_snippets = {
        address: normalized_snippet(target_image, address)
        for address in target_candidates
    }
    matches: list[RoleMatch] = []
    for label, reference_address in roles:
        reference = normalized_snippet(reference_image, reference_address)
        addresses = tuple(
            address
            for address, snippet in target_snippets.items()
            if snippet == reference
        )
        matches.append(RoleMatch(label, reference_address, addresses))
    return tuple(matches)


def markdown_report(
    reference_label: str,
    target_label: str,
    matches: tuple[RoleMatch, ...],
) -> str:
    lines = [
        f"# {reference_label} / {target_label} Symbolic Role Matches",
        "",
        "Exact normalized matches are relocation candidates, not proof that an",
        "entire subsystem is behaviorally identical. Ambiguous and unmatched roles",
        "require manual source inspection.",
        "",
        "| Role | Reference | Target candidates | Result |",
        "| --- | ---: | --- | --- |",
    ]
    for match in matches:
        targets = ", ".join(f"`0x{address:04x}`" for address in match.target_addresses)
        if not targets:
            targets = "none"
        result = "exact" if len(match.target_addresses) == 1 else (
            "unmatched" if not match.target_addresses else "ambiguous"
        )
        lines.append(
            f"| `{match.label}` | `0x{match.reference_address:04x}` | "
            f"{targets} | {result} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference-label", required=True)
    parser.add_argument("--reference-game-dir", required=True, type=Path)
    parser.add_argument("--reference-exe", required=True, type=Path)
    parser.add_argument("--target-label", required=True)
    parser.add_argument("--target-game-dir", required=True, type=Path)
    parser.add_argument("--target-exe", required=True, type=Path)
    parser.add_argument("--role", action="append", default=[], type=parse_role)
    parser.add_argument("--sq2-subsystems", action="store_true")
    parser.add_argument("--candidate", action="append", default=[], type=lambda value: int(value, 0))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    roles = list(args.role)
    if args.sq2_subsystems:
        roles.extend((pair.label, pair.sq2_handler) for pair in SUBSYSTEM_PAIRS)
    if not roles:
        parser.error("provide --role or --sq2-subsystems")

    reference = load_build(
        args.reference_label,
        args.reference_game_dir,
        args.reference_exe,
    )
    target = load_build(args.target_label, args.target_game_dir, args.target_exe)
    table_handlers = tuple(
        entry.handler for entry in (*target.actions, *target.conditions)
    )
    same_addresses = tuple(address for _label, address in roles)
    candidates = candidate_addresses(
        target.image,
        table_handlers=table_handlers,
        additional=tuple(args.candidate) + same_addresses,
    )
    matches = match_roles(reference.image, target.image, tuple(roles), candidates)
    report = markdown_report(args.reference_label, args.target_label, matches)
    if args.output is None:
        print(report)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="ascii")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
