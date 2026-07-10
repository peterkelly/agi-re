#!/usr/bin/env python3
"""Tests for script-visible resource reference auditing."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from resource_reference_audit import audit_game  # noqa: E402


ACTION_META_SIGNATURE = (
    (0, 0x00),
    (1, 0x80),
    (1, 0x80),
    (2, 0x80),
    (2, 0xC0),
    (2, 0x80),
    (2, 0xC0),
    (2, 0x80),
    (2, 0xC0),
    (2, 0xC0),
    (2, 0xC0),
    (2, 0x80),
    (1, 0x00),
    (1, 0x00),
    (1, 0x00),
    (1, 0x80),
)

CONDITION_META_SIGNATURE = (
    (0, 0x00),
    (2, 0x80),
    (2, 0xC0),
    (2, 0x80),
    (2, 0xC0),
    (2, 0x80),
    (2, 0xC0),
    (1, 0x00),
    (1, 0x80),
    (1, 0x00),
    (2, 0x40),
    (5, 0x00),
    (1, 0x00),
    (0, 0x00),
    (0, 0x00),
    (2, 0x00),
    (5, 0x00),
    (5, 0x00),
    (5, 0x00),
)


def dir_entry(volume: int, offset: int) -> bytes:
    return bytes(
        [
            ((volume & 0x0F) << 4) | ((offset >> 16) & 0x0F),
            (offset >> 8) & 0xFF,
            offset & 0xFF,
        ]
    )


def put_table_entry(data: bytearray, base: int, opcode: int, argc: int, meta: int) -> None:
    off = base + opcode * 4
    data[off : off + 4] = b"\x00\x00" + bytes([argc, meta])


def make_agidata() -> bytes:
    data = bytearray(b"\xcc" * 0x600)
    action_base = 0x20
    condition_base = 0x400
    for opcode, (argc, meta) in enumerate(ACTION_META_SIGNATURE):
        put_table_entry(data, action_base, opcode, argc, meta)
    put_table_entry(data, action_base, 0x62, 1, 0x00)
    put_table_entry(data, action_base, 0x63, 2, 0x00)
    for opcode, (argc, meta) in enumerate(CONDITION_META_SIGNATURE):
        put_table_entry(data, condition_base, opcode, argc, meta)
    return bytes(data)


def make_game(root: Path) -> Path:
    game = root / "AUDIT"
    game.mkdir()
    code = bytes([0x62, 0x02, 0x63, 0x22, 0x05, 0x00])
    logic_payload = len(code).to_bytes(2, "little") + code + b"\x00"
    (game / "LOGDIR").write_bytes(dir_entry(0, 0) + b"\xff\xff\xff")
    (game / "PICDIR").write_bytes(b"\xff\xff\xff")
    (game / "VIEWDIR").write_bytes(b"\xff\xff\xff")
    snddir = bytearray(b"\xff\xff\xff" * 35)
    snddir[2 * 3 : 2 * 3 + 3] = dir_entry(0, 0x40)
    snddir[34 * 3 : 34 * 3 + 3] = dir_entry(0, 0x70)
    (game / "SNDDIR").write_bytes(bytes(snddir))

    vol = bytearray(b"\x00" * 0x90)
    vol[0 : 5 + len(logic_payload)] = b"\x12\x34\x00" + len(logic_payload).to_bytes(2, "little") + logic_payload
    vol[0x40 : 0x48] = b"\x12\x34\x00\x03\x00snd"
    vol[0x70 : 0x75] = b"BAD!!"
    (game / "VOL.0").write_bytes(bytes(vol))
    (game / "AGIDATA.OVL").write_bytes(make_agidata())
    return game


class ResourceReferenceAuditTests(unittest.TestCase):
    def test_audit_reports_referenced_unreadable_resources(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            game = make_game(Path(temp_dir))
            report = audit_game(game)

        self.assertEqual(report["references"]["sound"], [2, 34])
        self.assertEqual(report["resources"]["sound"]["readable"], [2])
        self.assertEqual(report["referenced_unreadable"]["sound"], [34])
        self.assertEqual(report["unreferenced_unreadable"]["sound"], [])


if __name__ == "__main__":
    unittest.main()
