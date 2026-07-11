from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

from brush_table_audit import find_picture_scanner  # noqa: E402


class BrushTableAuditTests(unittest.TestCase):
    def test_picture_scanner_is_found_structurally(self) -> None:
        image = bytearray(0x100)
        address = 0x40
        image[address : address + 23] = bytes.fromhex(
            "ac 3c ff 74 10 2c f0 72 0c 3c 0a 77 08 "
            "8a d8 32 ff d1 e3 ff 97 d6 15"
        )
        scanner = find_picture_scanner(bytes(image))
        self.assertEqual(scanner.address, address)
        self.assertEqual(scanner.last_command, 0xFA)
        self.assertEqual(scanner.dispatch_offset, 0x15D6)


if __name__ == "__main__":
    unittest.main()
