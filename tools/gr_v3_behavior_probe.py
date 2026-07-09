#!/usr/bin/env python3
"""Targeted behavior probes for the local Gold Rush AGI v3 interpreter."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path


ROOM_REMAP_DESTINATION = 0x49
ROOM_REMAP_ALIAS = 0x7E
ROOM_REMAP_ALIASES = (0x7E, 0x7F, 0x80)
GR_KEY_MAP_SLOT_COUNT = 0x31
SQ2_KEY_MAP_SLOT_COUNT = 0x27
KEY_MAP_TEST_PICTURE = 1
KEY_MAP_TEST_STATUS = 7
KEY_MAP_TEST_KEY_WORD = ord("x")
DEFAULT_FIXTURE_ROOT = Path("build/gr-v3-behavior/room-remap-fixtures")
DEFAULT_OUTPUT = Path("build/gr-v3-behavior/room_remap_001.json")
DEFAULT_SNAPSHOT_RAW = Path("build/gr-v3-behavior/snapshot/room_remap.raw")
DEFAULT_SNAPSHOT_QCOW = Path("build/gr-v3-behavior/snapshot/room_remap.qcow2")


@dataclass(frozen=True)
class RoomRemapCase:
    label: str
    target_room: int
    fixture: Path
    dos_dir: str
    capture: Path


@dataclass(frozen=True)
class ProbeCase:
    label: str
    fixture: Path
    dos_dir: str
    capture: Path
    post_launch_keys: str = ""
    post_launch_wait: float = 0.0
    post_launch_key_delay: float = 0.03
    post_launch_after_text_wait: float = 0.0


def switch_room_payload(room_no: int, guard_var: int = 0xFA) -> bytes:
    from qemu_fixture import assignn_action, if_then, logic_resource, var_eq_imm_condition

    if not 0 <= room_no <= 0xFF:
        raise ValueError("room number must fit in one byte")
    if not 0 <= guard_var <= 0xFF:
        raise ValueError("guard variable must fit in one byte")
    switch_once = assignn_action(guard_var, 1) + bytes([0x12, room_no])
    return logic_resource(if_then(var_eq_imm_condition(guard_var, 0), switch_once) + bytes([0x17, 0x00, 0x00]))


def key_map_capacity_payload(
    *,
    picture_no: int = KEY_MAP_TEST_PICTURE,
    target_key_word: int = KEY_MAP_TEST_KEY_WORD,
    status_index: int = KEY_MAP_TEST_STATUS,
    dummy_count: int = GR_KEY_MAP_SLOT_COUNT - 1,
    init_flag: int = 0xF9,
) -> bytes:
    from qemu_fixture import (
        end_action,
        if_then,
        load_show_picture_actions,
        logic_resource,
        map_key_event_action,
        not_flag_set_condition,
        set_flag_action,
        status_byte_condition,
    )

    if not 0 <= dummy_count < GR_KEY_MAP_SLOT_COUNT:
        raise ValueError("dummy mapping count must leave room for the target mapping")
    if not 0 <= init_flag <= 0xFF:
        raise ValueError("init flag must fit in one byte")

    setup = bytearray()
    for index in range(dummy_count):
        setup.extend(map_key_event_action(0x0101 + index, status_index + 1))
    setup.extend(map_key_event_action(target_key_word, status_index))
    setup.extend(set_flag_action(init_flag))

    per_cycle = if_then(status_byte_condition(status_index), load_show_picture_actions(picture_no))
    return logic_resource(if_then(not_flag_set_condition(init_flag), bytes(setup)) + per_cycle + end_action())


def build_direct_draw_fixture(
    game_dir: Path,
    fixture_root: Path,
    *,
    picture_no: int,
    dos_prefix: str = "GRD",
) -> ProbeCase:
    from qemu_fixture import build_v3_logic_fixture, picture_logic_payload

    fixture_root.mkdir(parents=True, exist_ok=True)
    fixture = fixture_root / "direct_draw"
    build_v3_logic_fixture(picture_logic_payload(picture_no), fixture, game_dir=game_dir, logic_no=0)
    return ProbeCase("direct_draw", fixture, f"{dos_prefix}0", fixture / "qemu_capture.ppm")


def build_room_remap_fixtures(
    game_dir: Path,
    fixture_root: Path,
    *,
    picture_no: int = ROOM_REMAP_DESTINATION,
    dos_prefix: str = "GRR",
) -> list[RoomRemapCase]:
    from qemu_fixture import build_v3_logic_fixture, patch_v3_logic_resource, picture_logic_payload

    fixture_root.mkdir(parents=True, exist_ok=True)
    cases = [("direct_49", ROOM_REMAP_DESTINATION)]
    cases.extend((f"alias_{alias:02x}", alias) for alias in ROOM_REMAP_ALIASES)
    built: list[RoomRemapCase] = []
    for index, (label, target_room) in enumerate(cases):
        fixture = fixture_root / label
        build_v3_logic_fixture(switch_room_payload(target_room), fixture, game_dir=game_dir, logic_no=0)
        patch_v3_logic_resource(fixture, picture_logic_payload(picture_no), logic_no=ROOM_REMAP_DESTINATION)
        built.append(
            RoomRemapCase(
                label=label,
                target_room=target_room,
                fixture=fixture,
                dos_dir=f"{dos_prefix}{index}",
                capture=fixture / "qemu_capture.ppm",
            )
        )
    return built


def build_key_map_capacity_fixtures(
    game_dir: Path,
    fixture_root: Path,
    *,
    picture_no: int = KEY_MAP_TEST_PICTURE,
    dos_prefix: str = "GRK",
) -> list[ProbeCase]:
    from qemu_fixture import build_v3_logic_fixture, picture_logic_payload

    fixture_root.mkdir(parents=True, exist_ok=True)
    direct_fixture = fixture_root / "direct_picture"
    build_v3_logic_fixture(picture_logic_payload(picture_no), direct_fixture, game_dir=game_dir, logic_no=0)

    key_fixture = fixture_root / "slot_48_key_map"
    build_v3_logic_fixture(key_map_capacity_payload(picture_no=picture_no), key_fixture, game_dir=game_dir, logic_no=0)

    no_key_fixture = fixture_root / "slot_48_no_key"
    build_v3_logic_fixture(key_map_capacity_payload(picture_no=picture_no), no_key_fixture, game_dir=game_dir, logic_no=0)

    return [
        ProbeCase("direct_picture", direct_fixture, f"{dos_prefix}0", direct_fixture / "qemu_capture.ppm"),
        ProbeCase(
            "slot_48_key_map",
            key_fixture,
            f"{dos_prefix}1",
            key_fixture / "qemu_capture.ppm",
            post_launch_keys="x",
            post_launch_wait=1.0,
            post_launch_key_delay=0.12,
            post_launch_after_text_wait=0.5,
        ),
        ProbeCase("slot_48_no_key", no_key_fixture, f"{dos_prefix}2", no_key_fixture / "qemu_capture.ppm"),
    ]


def run_room_remap_qemu(
    cases: list[RoomRemapCase],
    *,
    snapshot_raw: Path,
    snapshot_qcow: Path,
    boot_wait: float,
    draw_wait: float,
) -> dict[str, bool]:
    from qemu_snapshot import SnapshotFixtureCase, build_snapshot_boot_disk, run_snapshot_qemu_cases

    qemu_cases = [
        SnapshotFixtureCase(case.dos_dir, case.fixture, case.capture)
        for case in cases
    ]
    build_snapshot_boot_disk(qemu_cases, snapshot_raw, snapshot_qcow)
    run_snapshot_qemu_cases(snapshot_qcow, qemu_cases, boot_wait, draw_wait)
    direct_capture = cases[0].capture.read_bytes()
    return {
        case.label: case.capture.read_bytes() == direct_capture
        for case in cases[1:]
    }


def run_qemu_cases(
    cases: list[ProbeCase],
    *,
    snapshot_raw: Path,
    snapshot_qcow: Path,
    boot_wait: float,
    draw_wait: float,
) -> None:
    from qemu_snapshot import SnapshotFixtureCase, build_snapshot_boot_disk, run_snapshot_qemu_cases

    qemu_cases = [
        SnapshotFixtureCase(
            case.dos_dir,
            case.fixture,
            case.capture,
            post_launch_keys=case.post_launch_keys,
            post_launch_wait=case.post_launch_wait,
            post_launch_key_delay=case.post_launch_key_delay,
            post_launch_after_text_wait=case.post_launch_after_text_wait,
        )
        for case in cases
    ]
    build_snapshot_boot_disk(qemu_cases, snapshot_raw, snapshot_qcow)
    run_snapshot_qemu_cases(snapshot_qcow, qemu_cases, boot_wait, draw_wait)


def write_report(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def case_report(case: RoomRemapCase) -> dict:
    return {
        "label": case.label,
        "target_room": case.target_room,
        "fixture": str(case.fixture),
        "dos_dir": case.dos_dir,
        "capture": str(case.capture),
    }


def probe_case_report(case: ProbeCase) -> dict:
    return {
        "label": case.label,
        "fixture": str(case.fixture),
        "dos_dir": case.dos_dir,
        "capture": str(case.capture),
        "post_launch_keys": case.post_launch_keys,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", choices=("room-remap", "direct-draw", "key-map-capacity"), default="room-remap")
    parser.add_argument("--game-dir", type=Path, required=True)
    parser.add_argument("--fixture-root", type=Path, default=DEFAULT_FIXTURE_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--picture", type=int, default=ROOM_REMAP_DESTINATION)
    parser.add_argument("--dos-prefix", default="GRR")
    parser.add_argument("--run-qemu", action="store_true")
    parser.add_argument("--snapshot-raw", type=Path, default=DEFAULT_SNAPSHOT_RAW)
    parser.add_argument("--snapshot-qcow", type=Path, default=DEFAULT_SNAPSHOT_QCOW)
    parser.add_argument("--boot-wait", type=float, default=5.0)
    parser.add_argument("--draw-wait", type=float, default=8.0)
    args = parser.parse_args()

    if args.probe == "key-map-capacity":
        cases = build_key_map_capacity_fixtures(
            args.game_dir,
            args.fixture_root,
            picture_no=args.picture,
            dos_prefix=args.dos_prefix,
        )
        result: dict = {
            "probe": "gr_v3_key_map_slot_48_capacity",
            "game_dir": str(args.game_dir),
            "picture": args.picture,
            "sq2_slot_count": SQ2_KEY_MAP_SLOT_COUNT,
            "gr_slot_count": GR_KEY_MAP_SLOT_COUNT,
            "target_slot_index": GR_KEY_MAP_SLOT_COUNT - 1,
            "target_key_word": KEY_MAP_TEST_KEY_WORD,
            "target_status_index": KEY_MAP_TEST_STATUS,
            "expected_matches_direct": {
                "slot_48_key_map": True,
                "slot_48_no_key": False,
            },
            "cases": [probe_case_report(case) for case in cases],
            "qemu": {"ran": False},
        }
        if args.run_qemu:
            run_qemu_cases(
                cases,
                snapshot_raw=args.snapshot_raw,
                snapshot_qcow=args.snapshot_qcow,
                boot_wait=args.boot_wait,
                draw_wait=args.draw_wait,
            )
            direct_capture = cases[0].capture.read_bytes()
            matches_direct = {
                case.label: case.capture.read_bytes() == direct_capture
                for case in cases[1:]
            }
            expected_matches = result["expected_matches_direct"]
            passed = matches_direct == expected_matches
            result["qemu"] = {
                "ran": True,
                "passed": passed,
                "matches_direct": matches_direct,
                "snapshot_raw": str(args.snapshot_raw),
                "snapshot_qcow": str(args.snapshot_qcow),
            }
        write_report(args.output, result)
        print(args.output)
        if args.run_qemu and not result["qemu"]["passed"]:
            return 1
        return 0

    if args.probe == "direct-draw":
        case = build_direct_draw_fixture(
            args.game_dir,
            args.fixture_root,
            picture_no=args.picture,
            dos_prefix=args.dos_prefix,
        )
        result: dict = {
            "probe": "gr_v3_direct_draw_logic0",
            "game_dir": str(args.game_dir),
            "picture": args.picture,
            "cases": [probe_case_report(case)],
            "qemu": {"ran": False},
        }
        if args.run_qemu:
            run_qemu_cases(
                [case],
                snapshot_raw=args.snapshot_raw,
                snapshot_qcow=args.snapshot_qcow,
                boot_wait=args.boot_wait,
                draw_wait=args.draw_wait,
            )
            result["qemu"] = {
                "ran": True,
                "snapshot_raw": str(args.snapshot_raw),
                "snapshot_qcow": str(args.snapshot_qcow),
            }
        write_report(args.output, result)
        print(args.output)
        return 0

    cases = build_room_remap_fixtures(
        args.game_dir,
        args.fixture_root,
        picture_no=args.picture,
        dos_prefix=args.dos_prefix,
    )
    result: dict = {
        "probe": "gr_v3_room_remap_0x7e_0x80_to_0x49",
        "game_dir": str(args.game_dir),
        "picture": args.picture,
        "cases": [case_report(case) for case in cases],
        "qemu": {"ran": False},
    }
    if args.run_qemu:
        captures_equal = run_room_remap_qemu(
            cases,
            snapshot_raw=args.snapshot_raw,
            snapshot_qcow=args.snapshot_qcow,
            boot_wait=args.boot_wait,
            draw_wait=args.draw_wait,
        )
        result["qemu"] = {
            "ran": True,
            "captures_equal": all(captures_equal.values()),
            "matches_direct": captures_equal,
            "snapshot_raw": str(args.snapshot_raw),
            "snapshot_qcow": str(args.snapshot_qcow),
        }
    write_report(args.output, result)
    print(args.output)
    if args.run_qemu and not result["qemu"]["captures_equal"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
