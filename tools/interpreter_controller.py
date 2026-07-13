#!/usr/bin/env python3
"""Persistent, cycle-controlled QEMU frontend for the original interpreter.

The controller uses only local project evidence and general QEMU interfaces:

* QMP owns VM lifecycle, keyboard events, screenshots, and snapshots.
* QEMU's GDB remote stub supplies semantic breakpoints and read-only state.
* A localhost HTTP API exposes stable, cycle-numbered interpreter state.

The selected game is always explicit.  Private game inputs are copied into a
generated session disk; this program never patches or writes under ``games/``.

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!! WARNING: THIS IS NOT YET A GENERIC AGI INTERPRETER CONTROLLER.           !!!
!!!                                                                         !!!
!!! Only the QMP/GDB transport and HTTP orchestration layers are intended   !!!
!!! to be version-neutral.  The sole runtime profile, executable signature  !!!
!!! anchor, hook/stack addresses, DS layout, object decoder, logical-buffer  !!!
!!! format, and dialog appearance have been validated only for SQ1.22's     !!!
!!! AGI 2.917 interpreter.  Do not add another game by copying this profile !!!
!!! and changing its hash.  Each interpreter build needs fresh local        !!!
!!! evidence for every profile field and every decoder/visual assumption.   !!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
"""

from __future__ import annotations

import argparse
import hashlib
import http.server
import json
import shutil
import socket
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from decrypt_agi import transform
from qemu_snapshot import mtools_image, qemu_vga_args, remove_dos_dir


EGA_PALETTE = (
    (0x00, 0x00, 0x00),
    (0x00, 0x00, 0xAA),
    (0x00, 0xAA, 0x00),
    (0x00, 0xAA, 0xAA),
    (0xAA, 0x00, 0x00),
    (0xAA, 0x00, 0xAA),
    (0xAA, 0x55, 0x00),
    (0xAA, 0xAA, 0xAA),
    (0x55, 0x55, 0x55),
    (0x55, 0x55, 0xFF),
    (0x55, 0xFF, 0x55),
    (0x55, 0xFF, 0xFF),
    (0xFF, 0x55, 0x55),
    (0xFF, 0x55, 0xFF),
    (0xFF, 0xFF, 0x55),
    (0xFF, 0xFF, 0xFF),
)


class ControllerError(RuntimeError):
    """An API-safe controller failure."""


class QmpError(ControllerError):
    """A QMP command failed."""


class GdbRemoteError(ControllerError):
    """The QEMU GDB remote stub returned an invalid or error response."""


@dataclass(frozen=True)
class InterpreterProfile:
    """Version-specific offsets; every field requires per-build evidence."""

    name: str
    version: str
    decrypted_sha256: str
    runtime_signature_offset: int
    cycle_boundary: int
    modal_wait: int
    modal_wait_return: int
    string_prompt_wait: int
    string_prompt_wait_return: int
    variables: int
    flags: int
    object_start_pointer: int
    object_end_pointer: int
    inventory_start_pointer: int
    inventory_end_pointer: int
    inventory_length: int
    logic_cache_head: int
    current_logic_pointer: int
    logical_buffer_segment: int
    window_active: int
    general_modal_active: int
    mapped_status_bytes: int
    logical_width: int = 160
    logical_height: int = 168
    object_record_size: int = 43

    def hooks(self) -> dict[str, int]:
        return {
            "cycle_boundary": self.cycle_boundary,
            "modal_wait": self.modal_wait,
            "string_prompt_wait": self.string_prompt_wait,
        }


SQ122_PROFILE = InterpreterProfile(
    # =======================================================================
    # WARNING: EVERY VALUE IN THIS PROFILE IS SQ1.22 / AGI 2.917 SPECIFIC.
    # A new game/interpreter profile must be derived and validated from that
    # local executable and data image.  The SHA-256 check prevents accidental
    # use of these offsets with a different decoded interpreter.
    # =======================================================================
    name="sq1_22_agi_2_917",
    version="2.917",
    decrypted_sha256="97dbc528ff4588b424d8c4e43035d619588c0c6b4376cc1ddea1fb83cea67656",
    runtime_signature_offset=0x0150,
    cycle_boundary=0x015B,
    # Both hooks are in visible modal/input loops, one nonblocking instruction
    # before the event wait.  That placement lets the debugger step off the
    # breakpoint before QEMU must receive the input that unblocks the wait.
    modal_wait=0x1D1B,
    modal_wait_return=0x1D25,
    string_prompt_wait=0x0DF2,
    string_prompt_wait_return=0x0DF8,
    variables=0x0009,
    flags=0x0109,
    object_start_pointer=0x0963,
    object_end_pointer=0x0965,
    inventory_start_pointer=0x0969,
    inventory_end_pointer=0x096B,
    inventory_length=0x096D,
    logic_cache_head=0x096F,
    current_logic_pointer=0x0979,
    logical_buffer_segment=0x1365,
    window_active=0x0D15,
    general_modal_active=0x0615,
    mapped_status_bytes=0x1210,
)


PROFILES = {SQ122_PROFILE.name: SQ122_PROFILE}


def u16le(data: bytes, offset: int = 0) -> int:
    return int.from_bytes(data[offset : offset + 2], "little")


def mz_image(data: bytes) -> bytes:
    if data[:2] != b"MZ":
        raise ControllerError("decoded interpreter is not an MZ executable")
    header_size = u16le(data, 0x08) * 16
    if header_size <= 0 or header_size >= len(data):
        raise ControllerError(f"invalid MZ header size {header_size:#x}")
    return data[header_size:]


def decode_interpreter(game_dir: Path) -> bytes:
    # PROFILE-SPECIFIC PACKAGING/LOADER WARNING: these filenames and the
    # locally observed loader transform are only validated for current inputs.
    loader = (game_dir / "SIERRA.COM").read_bytes()
    encrypted = (game_dir / "AGI").read_bytes()
    return transform(loader, encrypted)


def validate_profile(game_dir: Path, profile: InterpreterProfile) -> bytes:
    decoded = decode_interpreter(game_dir)
    digest = hashlib.sha256(decoded).hexdigest()
    if digest != profile.decrypted_sha256:
        raise ControllerError(
            f"{profile.name} expects decoded interpreter SHA-256 "
            f"{profile.decrypted_sha256}, got {digest}"
        )
    return mz_image(decoded)


def prepare_session_disk(
    *,
    base_image: Path,
    game_dir: Path,
    dos_game_dir: str,
    raw_output: Path,
    qcow_output: Path,
) -> Path:
    """Copy a private game into a disposable raw clone and convert to qcow2."""
    if not base_image.exists():
        raise ControllerError(f"base FreeDOS image does not exist: {base_image}")
    required = ("SIERRA.COM", "AGI", "AGIDATA.OVL")
    missing = [name for name in required if not (game_dir / name).exists()]
    if missing:
        raise ControllerError(f"game directory is missing: {', '.join(missing)}")
    if not dos_game_dir or len(dos_game_dir) > 8 or not dos_game_dir.isalnum():
        raise ControllerError("DOS game directory must be 1-8 alphanumeric characters")

    raw_output.parent.mkdir(parents=True, exist_ok=True)
    qcow_output.parent.mkdir(parents=True, exist_ok=True)
    raw_output.unlink(missing_ok=True)
    qcow_output.unlink(missing_ok=True)
    shutil.copyfile(base_image, raw_output)
    image = mtools_image(raw_output)
    remove_dos_dir(image, dos_game_dir)
    subprocess.run(["mmd", "-i", image, f"::/{dos_game_dir}"], check=True)
    files = sorted(str(path) for path in game_dir.iterdir() if path.is_file())
    subprocess.run(
        ["mcopy", "-o", "-i", image, *files, f"::/{dos_game_dir}"],
        check=True,
    )
    subprocess.run(
        ["qemu-img", "convert", "-f", "raw", "-O", "qcow2", str(raw_output), str(qcow_output)],
        check=True,
    )
    return qcow_output


class QmpClient:
    """Small synchronous QMP client with event buffering."""

    def __init__(self, path: Path, timeout: float = 10.0):
        self.path = path
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)
        self.sock.connect(str(path))
        self.stream = self.sock.makefile("rwb", buffering=0)
        self.lock = threading.RLock()
        self.next_id = 1
        self.events: list[dict[str, Any]] = []
        greeting = self._read_message()
        if "QMP" not in greeting:
            raise QmpError(f"invalid QMP greeting: {greeting}")
        self.execute("qmp_capabilities")

    def close(self) -> None:
        try:
            self.stream.close()
        finally:
            self.sock.close()

    def _read_message(self) -> dict[str, Any]:
        while True:
            raw = self.stream.readline()
            if not raw:
                raise QmpError("QMP connection closed")
            raw = raw.strip()
            if raw:
                return json.loads(raw)

    def execute(self, command: str, arguments: dict[str, Any] | None = None) -> Any:
        with self.lock:
            request_id = self.next_id
            self.next_id += 1
            request: dict[str, Any] = {"execute": command, "id": request_id}
            if arguments:
                request["arguments"] = arguments
            self.stream.write(json.dumps(request, separators=(",", ":")).encode() + b"\r\n")
            while True:
                message = self._read_message()
                if "event" in message:
                    self.events.append(message)
                    continue
                if message.get("id") != request_id:
                    continue
                if "error" in message:
                    error = message["error"]
                    raise QmpError(f"{command}: {error.get('class')}: {error.get('desc')}")
                return message.get("return")

    def query_status(self) -> dict[str, Any]:
        result = self.execute("query-status")
        return result if isinstance(result, dict) else {}

    def stop(self) -> None:
        if self.query_status().get("running"):
            self.execute("stop")

    def cont(self) -> None:
        if not self.query_status().get("running"):
            self.execute("cont")

    def key_event(self, qcode: str, down: bool) -> None:
        self.execute(
            "input-send-event",
            {
                "events": [
                    {
                        "type": "key",
                        "data": {
                            "down": down,
                            "key": {"type": "qcode", "data": qcode},
                        },
                    }
                ]
            },
        )

    def screenshot(self, path: Path, image_format: str = "ppm") -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        args: dict[str, Any] = {"filename": str(path.resolve())}
        if image_format:
            args["format"] = image_format
        try:
            self.execute("screendump", args)
        except QmpError:
            args.pop("format", None)
            self.execute("screendump", args)
        return path

    def hmp(self, command: str) -> str:
        result = self.execute("human-monitor-command", {"command-line": command})
        return str(result or "")


class GdbRemoteClient:
    """Minimal i386 QEMU GDB remote protocol client."""

    REGISTER_NAMES = (
        "eax", "ecx", "edx", "ebx", "esp", "ebp", "esi", "edi",
        "eip", "eflags", "cs", "ss", "ds", "es", "fs", "gs",
    )

    def __init__(self, path: Path, timeout: float = 10.0):
        self.path = path
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)
        self.sock.connect(str(path))
        self.lock = threading.RLock()
        self._request("qSupported:multiprocess+;xmlRegisters=i386")

    def close(self) -> None:
        self.sock.close()

    @staticmethod
    def _checksum(payload: bytes) -> bytes:
        return f"{sum(payload) & 0xff:02x}".encode()

    def _send(self, payload: str) -> None:
        encoded = payload.encode("ascii")
        packet = b"$" + encoded + b"#" + self._checksum(encoded)
        self.sock.sendall(packet)
        while True:
            ack = self.sock.recv(1)
            if ack == b"+":
                return
            if ack == b"-":
                self.sock.sendall(packet)
                continue
            if not ack:
                raise GdbRemoteError("GDB remote closed while awaiting acknowledgement")

    def _receive(self, timeout: float | None = None) -> str:
        previous = self.sock.gettimeout()
        if timeout is not None:
            self.sock.settimeout(timeout)
        try:
            while True:
                marker = self.sock.recv(1)
                if not marker:
                    raise GdbRemoteError("GDB remote closed")
                if marker == b"$":
                    break
            data = bytearray()
            while True:
                byte = self.sock.recv(1)
                if byte == b"#":
                    break
                if not byte:
                    raise GdbRemoteError("truncated GDB remote packet")
                data.extend(byte)
            checksum = self.sock.recv(2)
            expected = self._checksum(bytes(data))
            if checksum.lower() != expected:
                self.sock.sendall(b"-")
                raise GdbRemoteError("GDB remote checksum mismatch")
            self.sock.sendall(b"+")
            payload = data.decode("ascii", errors="replace")
            if payload.startswith("E"):
                raise GdbRemoteError(f"GDB remote error {payload}")
            return payload
        finally:
            self.sock.settimeout(previous)

    def _request(self, payload: str, timeout: float | None = None) -> str:
        with self.lock:
            self._send(payload)
            return self._receive(timeout)

    def query_stop(self) -> str:
        return self._request("?")

    def interrupt(self, timeout: float = 5.0) -> str:
        with self.lock:
            self.sock.sendall(b"\x03")
            return self._receive(timeout)

    def read_memory(self, address: int, size: int, chunk_size: int = 0x1000) -> bytes:
        result = bytearray()
        for offset in range(0, size, chunk_size):
            count = min(chunk_size, size - offset)
            payload = self._request(f"m{address + offset:x},{count:x}")
            try:
                decoded = bytes.fromhex(payload)
            except ValueError as exc:
                raise GdbRemoteError(f"invalid memory response: {payload[:80]}") from exc
            if len(decoded) != count:
                raise GdbRemoteError(
                    f"short memory response at {address + offset:#x}: {len(decoded)} != {count}"
                )
            result.extend(decoded)
        return bytes(result)

    def read_registers(self) -> dict[str, int]:
        payload = self._request("g")
        raw = bytes.fromhex(payload)
        if len(raw) < len(self.REGISTER_NAMES) * 4:
            raise GdbRemoteError(f"short i386 register response: {len(raw)} bytes")
        return {
            name: int.from_bytes(raw[index * 4 : index * 4 + 4], "little")
            for index, name in enumerate(self.REGISTER_NAMES)
        }

    def add_breakpoint(self, address: int) -> None:
        reply = self._request(f"Z0,{address:x},1")
        if reply != "OK":
            raise GdbRemoteError(f"cannot add breakpoint at {address:#x}: {reply}")

    def remove_breakpoint(self, address: int) -> None:
        reply = self._request(f"z0,{address:x},1")
        if reply not in ("OK", ""):
            raise GdbRemoteError(f"cannot remove breakpoint at {address:#x}: {reply}")

    def single_step(self, timeout: float = 5.0) -> str:
        return self._request("s", timeout)

    def continue_async(self) -> None:
        with self.lock:
            self._send("c")

    def wait_stop(self, timeout: float | None = None) -> str:
        with self.lock:
            return self._receive(timeout)


def find_runtime_image_base(
    gdb: GdbRemoteClient,
    image: bytes,
    profile: InterpreterProfile,
    start: int = 0x00000,
    end: int = 0xA0000,
) -> int:
    """Find the paragraph-aligned loaded image from a relocation-free signature."""
    signature_offset = profile.runtime_signature_offset
    signature = image[signature_offset : signature_offset + 32]
    if len(signature) != 32:
        raise ControllerError("interpreter image is too short for cycle signature")
    overlap = len(signature) - 1
    previous = b""
    matches: list[int] = []
    for address in range(start, end, 0x4000):
        block = gdb.read_memory(address, min(0x4000, end - address))
        haystack = previous + block
        base_address = address - len(previous)
        cursor = 0
        while True:
            found = haystack.find(signature, cursor)
            if found < 0:
                break
            runtime_signature = base_address + found
            image_base = runtime_signature - signature_offset
            if image_base >= 0 and image_base % 16 == 0:
                matches.append(image_base)
            cursor = found + 1
        previous = haystack[-overlap:]
    unique = sorted(set(matches))
    if len(unique) != 1:
        raise ControllerError(f"expected one loaded interpreter image, found {unique}")
    return unique[0]


def unpack_flags(packed: bytes) -> list[bool]:
    """Decode the high-bit-first flag layout observed in SQ1.22/2.917."""
    return [bool(packed[index // 8] & (0x80 >> (index % 8))) for index in range(len(packed) * 8)]


def parse_object_records(data: bytes, start_offset: int, record_size: int = 43) -> list[dict[str, Any]]:
    """Decode the observed SQ1.22/AGI-2.917 43-byte object-record layout.

    WARNING: ``record_size`` alone does not make this decoder portable.  Every
    field offset below must be revalidated before another interpreter profile
    uses it.
    """
    if record_size != 43:
        raise ControllerError(
            f"no object-record decoder is implemented for {record_size}-byte records"
        )
    if len(data) % record_size:
        raise ControllerError(f"object table length {len(data):#x} is not a multiple of {record_size}")
    objects: list[dict[str, Any]] = []
    for index in range(len(data) // record_size):
        record = data[index * record_size : (index + 1) * record_size]
        objects.append(
            {
                "index": index,
                "offset": start_offset + index * record_size,
                "x": u16le(record, 0x03),
                "y": u16le(record, 0x05),
                "view": record[0x07],
                "loop": record[0x0A],
                "loop_count": record[0x0B],
                "cel": record[0x0E],
                "width": u16le(record, 0x1A),
                "height": u16le(record, 0x1C),
                "step_size": record[0x1E],
                "cycle_time": record[0x1F],
                "cycle_count": record[0x20],
                "direction": record[0x21],
                "motion_mode": record[0x22],
                "cycle_mode": record[0x23],
                "priority": record[0x24],
                "flags": u16le(record, 0x25),
                "target_x_or_parameter": record[0x27],
                "target_y_or_parameter": record[0x28],
                "completion_flag": record[0x2A],
                "raw_hex": record.hex(),
            }
        )
    return objects


def classify_blocking_stack(stack: bytes, profile: InterpreterProfile) -> str | None:
    """Identify profile-specific blocking UI loops from near return addresses."""
    words = {u16le(stack, offset) for offset in range(0, len(stack) - 1, 2)}
    if profile.string_prompt_wait_return in words:
        return "string_prompt_wait"
    if profile.modal_wait_return in words:
        return "modal_wait"
    return None


def colorize_logical_buffer(buffer: bytes, channel: str, width: int = 160, height: int = 168) -> bytes:
    """Render the SQ1.22/2.917 low-visual/high-priority nibble layout."""
    if len(buffer) != width * height:
        raise ControllerError(f"logical buffer has {len(buffer)} bytes, expected {width * height}")
    if channel not in ("visual", "priority"):
        raise ControllerError("channel must be visual or priority")
    indices = ((value & 0x0F) if channel == "visual" else (value >> 4) for value in buffer)
    pixels = bytearray()
    for index in indices:
        pixels.extend(EGA_PALETTE[index])
    return f"P6\n{width} {height}\n255\n".encode() + bytes(pixels)


def parse_ppm(data: bytes) -> tuple[int, int, bytes]:
    if not data.startswith(b"P6"):
        raise ControllerError("dialog detector requires a binary P6 PPM")
    position = 2
    tokens: list[bytes] = []
    while len(tokens) < 3:
        while position < len(data) and data[position] in b" \t\r\n":
            position += 1
        if position < len(data) and data[position] == ord("#"):
            position = data.index(b"\n", position) + 1
            continue
        end = position
        while end < len(data) and data[end] not in b" \t\r\n":
            end += 1
        tokens.append(data[position:end])
        position = end
    while position < len(data) and data[position] in b" \t\r\n":
        position += 1
    width, height, maximum = (int(token) for token in tokens)
    if maximum != 255:
        raise ControllerError(f"unsupported PPM maximum {maximum}")
    pixels = data[position:]
    if len(pixels) != width * height * 3:
        raise ControllerError("truncated PPM pixel data")
    return width, height, pixels


def detect_modal_borders(ppm: bytes) -> list[dict[str, int]]:
    """Find the red/white modal appearance observed in SQ1.22 under EGA.

    WARNING: this is a game/version/display-specific screen oracle.  Other
    profiles must validate their own modal appearance or supply another
    detector.
    """
    width, height, pixels = parse_ppm(ppm)
    def pixel(x: int, y: int) -> tuple[int, int, int]:
        offset = (y * width + x) * 3
        return tuple(pixels[offset : offset + 3])  # type: ignore[return-value]

    def is_red(value: tuple[int, int, int]) -> bool:
        return value[0] >= 150 and value[1] <= 24 and value[2] <= 24

    def is_white(value: tuple[int, int, int]) -> bool:
        return min(value) >= 235

    runs_by_y: dict[int, list[tuple[int, int]]] = {}
    minimum_width = max(40, width // 8)
    for y in range(height):
        runs: list[tuple[int, int]] = []
        x = 0
        while x < width:
            if not is_red(pixel(x, y)):
                x += 1
                continue
            start = x
            while x < width and is_red(pixel(x, y)):
                x += 1
            if x - start >= minimum_width:
                runs.append((start, x - 1))
        if runs:
            runs_by_y[y] = runs

    boxes: list[dict[str, int]] = []
    for top, runs in runs_by_y.items():
        for left, right in runs:
            last_bottom = min(height - 1, top + height // 2)
            for bottom in range(top + max(12, height // 30), last_bottom + 1):
                if (left, right) not in runs_by_y.get(bottom, []):
                    continue
                vertical = bottom - top + 1
                left_hits = sum(is_red(pixel(left, y)) for y in range(top, bottom + 1))
                right_hits = sum(is_red(pixel(right, y)) for y in range(top, bottom + 1))
                if left_hits / vertical < 0.75 or right_hits / vertical < 0.75:
                    continue
                sample_y = (top + bottom) // 2
                white_hits = sum(
                    is_white(pixel(x, sample_y))
                    for x in range(left + 2, right - 1)
                )
                if white_hits < (right - left) // 3:
                    continue
                boxes.append({"left": left, "top": top, "right": right, "bottom": bottom})
                break
    deduplicated: list[dict[str, int]] = []
    for box in boxes:
        if any(
            all(abs(box[key] - existing[key]) <= 2 for key in ("left", "top", "right", "bottom"))
            for existing in deduplicated
        ):
            continue
        deduplicated.append(box)
    return deduplicated


def resolve_path(value: Any, path: str) -> Any:
    current = value
    for component in path.split("."):
        if isinstance(current, dict):
            if component not in current:
                raise ControllerError(f"predicate path does not exist: {path}")
            current = current[component]
        elif isinstance(current, list):
            try:
                current = current[int(component)]
            except (ValueError, IndexError) as exc:
                raise ControllerError(f"invalid list component in predicate path: {path}") from exc
        else:
            raise ControllerError(f"predicate path crosses a scalar: {path}")
    return current


def evaluate_predicate(state: dict[str, Any], predicate: dict[str, Any]) -> bool:
    if "all" in predicate:
        return all(evaluate_predicate(state, item) for item in predicate["all"])
    if "any" in predicate:
        return any(evaluate_predicate(state, item) for item in predicate["any"])
    path = str(predicate.get("path", ""))
    operator = str(predicate.get("op", "eq"))
    actual = resolve_path(state, path)
    expected = predicate.get("value")
    operations = {
        "eq": lambda: actual == expected,
        "ne": lambda: actual != expected,
        "lt": lambda: actual < expected,
        "le": lambda: actual <= expected,
        "gt": lambda: actual > expected,
        "ge": lambda: actual >= expected,
        "in": lambda: actual in expected,
        "contains": lambda: expected in actual,
        "between": lambda: expected[0] <= actual <= expected[1],
        "truthy": lambda: bool(actual),
        "falsy": lambda: not actual,
    }
    if operator not in operations:
        raise ControllerError(f"unsupported predicate operator: {operator}")
    return bool(operations[operator]())


QCODE_BY_CHARACTER = {
    " ": "spc", "\n": "ret", "\r": "ret", "\t": "tab",
    ".": "dot", ",": "comma", "-": "minus", "=": "equal",
    "/": "slash", "\\": "backslash", ";": "semicolon",
}


def qcode_for_character(character: str) -> tuple[str, bool]:
    if len(character) != 1:
        raise ControllerError("character input must contain exactly one character")
    if character.isalpha():
        return character.lower(), character.isupper()
    if character.isdigit():
        return character, False
    if character == ":":
        return "semicolon", True
    if character == "_":
        return "minus", True
    if character in QCODE_BY_CHARACTER:
        return QCODE_BY_CHARACTER[character], False
    raise ControllerError(f"unsupported keyboard character: {character!r}")


@dataclass
class ManagedStop:
    reason: str
    address: int
    packet: str
    registers: dict[str, int]


@dataclass
class InterpreterSession:
    profile: InterpreterProfile
    image: bytes
    qmp: QmpClient
    gdb: GdbRemoteClient
    capture_dir: Path
    capture_every_cycle: bool = False
    runtime_image_base: int | None = None
    data_segment: int | None = None
    breakpoints: dict[int, str] = field(default_factory=dict)
    current_stop: ManagedStop | None = None
    cycle: int = 0
    state_revision: int = 0
    cached_state: dict[str, Any] = field(default_factory=dict)
    lock: threading.RLock = field(default_factory=threading.RLock)

    def discover(self, wait_for_hook: bool = True) -> dict[str, Any]:
        with self.lock:
            self.qmp.stop()
            packet = self.gdb.query_stop()
            base = self.runtime_image_base
            if base is None:
                base = find_runtime_image_base(self.gdb, self.image, self.profile)
            self.runtime_image_base = base
            # This QEMU real-mode GDB path reliably honors one execution
            # breakpoint at a time.  Normal operation therefore starts with
            # only the cycle hook and switches hooks when a blocking loop is
            # classified from its stack.
            self.select_breakpoints(["cycle_boundary"])
            registers = self.gdb.read_registers()
            self.data_segment = registers["ds"] & 0xFFFF
            if not wait_for_hook:
                self.current_stop = ManagedStop(
                    "instrumented_pause",
                    self._linear_ip(registers),
                    packet,
                    registers,
                )
                self.state_revision += 1
                self.cached_state = self.read_state()
                return self.cached_state
            self._continue_from_arbitrary_stop()
            stop = self.wait_for_stop(timeout=10.0)
            if stop.reason not in ("cycle_boundary", "modal_wait", "string_prompt_wait"):
                raise ControllerError(f"unexpected first semantic stop: {stop.reason}")
            self.data_segment = stop.registers["ds"] & 0xFFFF
            return self.read_state()

    def select_breakpoints(self, reasons: list[str]) -> dict[str, Any]:
        """Select active semantic hooks for targeted debugger diagnosis."""
        if self.runtime_image_base is None:
            raise ControllerError("interpreter has not been discovered")
        if self.qmp.query_status().get("running"):
            raise ControllerError("breakpoints can only be changed while stopped")
        available = self.profile.hooks()
        unknown = sorted(set(reasons) - set(available))
        if unknown:
            raise ControllerError(f"unknown breakpoint reasons: {', '.join(unknown)}")
        if len(reasons) > 1:
            raise ControllerError("this QEMU real-mode path supports one reliable hook at a time")
        for address in self.breakpoints:
            self.gdb.remove_breakpoint(address)
        self.breakpoints.clear()
        for reason in reasons:
            address = self.runtime_image_base + available[reason]
            self.gdb.add_breakpoint(address)
            self.breakpoints[address] = reason
        return self.read_debug_state()

    def resume(self) -> dict[str, Any]:
        with self.lock:
            if self.qmp.query_status().get("running"):
                raise ControllerError("VM is already running")
            if self.current_stop and self.current_stop.address in self.breakpoints:
                self._step_over_current_breakpoint()
            else:
                self.current_stop = None
            self.gdb.continue_async()
            return {"running": True, "cycle": self.cycle}

    def wait(self, timeout: float = 2.0) -> dict[str, Any]:
        with self.lock:
            self.wait_for_semantic_stop(timeout)
            return self.cached_state

    def pause(self) -> dict[str, Any]:
        with self.lock:
            if self.qmp.query_status().get("running"):
                packet = self.gdb.interrupt()
            else:
                packet = self.gdb.query_stop()
            self.current_stop = self._decode_stop(packet)
            self.state_revision += 1
            if self.data_segment is not None:
                self.cached_state = self.read_state()
            return {
                "vm": self.qmp.query_status(),
                "stop_reason": self.current_stop.reason,
                "stop_address": self.current_stop.address,
            }

    def _continue_from_arbitrary_stop(self) -> None:
        self.current_stop = None
        self.gdb.continue_async()

    def _linear_ip(self, registers: dict[str, int]) -> int:
        return ((registers["cs"] & 0xFFFF) << 4) + (registers["eip"] & 0xFFFF)

    def _decode_stop(self, packet: str) -> ManagedStop:
        registers = self.gdb.read_registers()
        address = self._linear_ip(registers)
        reason = self.breakpoints.get(address, "debug_stop")
        return ManagedStop(reason, address, packet, registers)

    def wait_for_stop(self, timeout: float | None = None) -> ManagedStop:
        deadline = None if timeout is None else time.monotonic() + timeout
        while self.qmp.query_status().get("running"):
            if deadline is not None and time.monotonic() >= deadline:
                raise TimeoutError("interpreter did not reach a semantic stop")
            time.sleep(0.002)
        receive_timeout = None if deadline is None else max(0.1, deadline - time.monotonic())
        packet = self.gdb.wait_stop(receive_timeout)
        stop = self._decode_stop(packet)
        self.current_stop = stop
        if stop.reason == "cycle_boundary":
            self.cycle += 1
        self.state_revision += 1
        self.cached_state = self.read_state()
        if self.capture_every_cycle and stop.reason == "cycle_boundary":
            self.capture_cycle()
        return stop

    def interrupt_and_classify(self, timeout: float = 5.0) -> ManagedStop:
        """Interrupt a blocked interpreter and classify its caller stack."""
        if self.qmp.query_status().get("running"):
            packet = self.gdb.interrupt(timeout)
        else:
            packet = self.gdb.wait_stop(timeout)
        stop = self._decode_stop(packet)
        registers = stop.registers
        stack_address = ((registers["ss"] & 0xFFFF) << 4) + (registers["esp"] & 0xFFFF)
        stack = self.gdb.read_memory(stack_address, 256)
        stop.reason = classify_blocking_stack(stack, self.profile) or stop.reason
        self.current_stop = stop
        self.state_revision += 1
        self.cached_state = self.read_state()
        if stop.reason in ("string_prompt_wait", "modal_wait"):
            self.select_breakpoints([stop.reason])
            self.cached_state = self.read_state()
        return stop

    def wait_for_semantic_stop(self, timeout: float = 2.0) -> ManagedStop:
        try:
            return self.wait_for_stop(timeout)
        except TimeoutError:
            stop = self.interrupt_and_classify()
            if stop.reason not in ("string_prompt_wait", "modal_wait"):
                raise TimeoutError(
                    f"interpreter did not reach a semantic stop; interrupted at {stop.address:#x}"
                )
            return stop

    def _step_over_current_breakpoint(self) -> None:
        if self.current_stop is None:
            return
        address = self.current_stop.address
        if address not in self.breakpoints:
            return
        self.gdb.remove_breakpoint(address)
        try:
            self.gdb.single_step()
        finally:
            # QEMU's real-mode single-step path can discard other software
            # breakpoints.  Reinstall the entire semantic set.
            for breakpoint_address in self.breakpoints:
                self.gdb.add_breakpoint(breakpoint_address)
        self.current_stop = None

    def begin_resume(self) -> None:
        with self.lock:
            if self.qmp.query_status().get("running"):
                raise ControllerError("VM is already running")
            self._step_over_current_breakpoint()
            self.gdb.continue_async()

    def step_cycle(self, timeout: float = 2.0) -> dict[str, Any]:
        with self.lock:
            self.begin_resume()
            self.wait_for_semantic_stop(timeout)
            return self.cached_state

    def run_cycles(self, count: int, timeout: float = 2.0) -> dict[str, Any]:
        if count < 0 or count > 1_000_000:
            raise ControllerError("cycle count must be between 0 and 1000000")
        result = self.read_state()
        completed = 0
        while completed < count:
            result = self.step_cycle(timeout)
            if result["stop_reason"] != "cycle_boundary":
                break
            completed += 1
        result = dict(result)
        result["requested_cycles"] = count
        result["completed_cycles"] = completed
        return result

    def run_until(
        self,
        predicate: dict[str, Any],
        max_cycles: int,
        timeout: float = 2.0,
    ) -> dict[str, Any]:
        state = self.read_state()
        if evaluate_predicate(state, predicate):
            return {**state, "matched": True, "cycles_run": 0}
        for index in range(1, max_cycles + 1):
            state = self.step_cycle(timeout)
            if evaluate_predicate(state, predicate):
                return {**state, "matched": True, "cycles_run": index}
            if state["stop_reason"] != "cycle_boundary":
                return {**state, "matched": False, "cycles_run": index, "stopped_early": True}
        return {**state, "matched": False, "cycles_run": max_cycles}

    def _require_data_segment(self) -> int:
        if self.data_segment is None:
            raise ControllerError("interpreter has not been discovered")
        return self.data_segment

    def read_data(self, offset: int, size: int) -> bytes:
        if self.qmp.query_status().get("running"):
            raise ControllerError("interpreter memory is only coherent at a semantic stop")
        segment = self._require_data_segment()
        return self.gdb.read_memory((segment << 4) + offset, size)

    def read_word(self, offset: int) -> int:
        return u16le(self.read_data(offset, 2))

    def read_variables(self) -> list[int]:
        return list(self.read_data(self.profile.variables, 256))

    def read_flags(self) -> list[bool]:
        return unpack_flags(self.read_data(self.profile.flags, 32))

    def read_objects(self) -> list[dict[str, Any]]:
        start = self.read_word(self.profile.object_start_pointer)
        end = self.read_word(self.profile.object_end_pointer)
        if end < start or end - start > self.profile.object_record_size * 256:
            raise ControllerError(f"invalid object table bounds {start:#x}..{end:#x}")
        return parse_object_records(
            self.read_data(start, end - start),
            start,
            self.profile.object_record_size,
        )

    def read_inventory(self) -> list[dict[str, Any]]:
        # PROFILE-SPECIFIC FORMAT: 3-byte entry and 0xff carried marker were
        # validated for SQ1.22/2.917 only.
        start = self.read_word(self.profile.inventory_start_pointer)
        end = self.read_word(self.profile.inventory_end_pointer)
        if end < start or (end - start) % 3 or end - start > 3 * 256:
            raise ControllerError(f"invalid inventory table bounds {start:#x}..{end:#x}")
        table = self.read_data(start, end - start)
        result: list[dict[str, Any]] = []
        for index in range(len(table) // 3):
            name_offset = u16le(table, index * 3)
            marker = table[index * 3 + 2]
            name = ""
            try:
                raw_name = self.read_data(start + name_offset, 128).split(b"\0", 1)[0]
                name = raw_name.decode("cp437", errors="replace")
            except (ControllerError, GdbRemoteError):
                pass
            result.append(
                {
                    "index": index,
                    "name": name,
                    "name_offset": name_offset,
                    "room_or_marker": marker,
                    "carried": marker == 0xFF,
                }
            )
        return result

    def read_logics(self) -> list[dict[str, Any]]:
        # PROFILE-SPECIFIC FORMAT: record width/field offsets below are the
        # observed SQ1.22/2.917 logic-cache representation.
        head = self.profile.logic_cache_head
        records: list[dict[str, Any]] = []
        pointer = self.read_word(head)
        seen: set[int] = set()
        while pointer and pointer not in seen and len(records) < 256:
            seen.add(pointer)
            raw = self.read_data(pointer, 10)
            records.append(
                {
                    "offset": pointer,
                    "next": u16le(raw, 0),
                    "logic": raw[2],
                    "entry_ip": u16le(raw, 4),
                    "resume_ip": u16le(raw, 6),
                    "raw_hex": raw.hex(),
                }
            )
            pointer = u16le(raw, 0)
        current = self.read_word(self.profile.current_logic_pointer)
        for record in records:
            record["current"] = record["offset"] == current
        return records

    def read_logical_buffer(self) -> bytes:
        segment = self.read_word(self.profile.logical_buffer_segment)
        if not segment:
            raise ControllerError("logical picture buffer has not been allocated")
        return self.gdb.read_memory(
            segment << 4,
            self.profile.logical_width * self.profile.logical_height,
        )

    def read_state(self) -> dict[str, Any]:
        if self.data_segment is None:
            return {
                "profile": self.profile.name,
                "instrumented": False,
                "cycle": self.cycle,
                "state_revision": self.state_revision,
                "vm": self.qmp.query_status(),
            }
        vm = self.qmp.query_status()
        if vm.get("running"):
            if self.cached_state:
                state = dict(self.cached_state)
                state.update({"stop_reason": "running", "stale": True, "vm": vm})
                return state
            return {
                "profile": self.profile.name,
                "version": self.profile.version,
                "instrumented": True,
                "cycle": self.cycle,
                "state_revision": self.state_revision,
                "stop_reason": "running",
                "stale": True,
                "vm": vm,
            }
        variables = self.read_variables()
        flags = self.read_flags()
        objects = self.read_objects()
        stop_reason = self.current_stop.reason if self.current_stop else "running"
        # PROFILE-SPECIFIC SEMANTICS: v0..v3 meanings are validated for the
        # current SQ1.22/2.917 profile and must be checked for future profiles.
        return {
            "profile": self.profile.name,
            "version": self.profile.version,
            "instrumented": True,
            "cycle": self.cycle,
            "state_revision": self.state_revision,
            "stop_reason": stop_reason,
            "stop_address": self.current_stop.address if self.current_stop else None,
            "runtime_image_base": self.runtime_image_base,
            "data_segment": self.data_segment,
            "room": variables[0],
            "previous_room": variables[1],
            "entry_boundary": variables[2],
            "score": variables[3],
            "variables": variables,
            "flags": flags,
            "objects": objects,
            "window_active": bool(self.read_word(self.profile.window_active)),
            "general_modal_active": bool(self.read_word(self.profile.general_modal_active)),
            "vm": vm,
        }

    def read_debug_state(self, stack_bytes: int = 64) -> dict[str, Any]:
        if self.qmp.query_status().get("running"):
            raise ControllerError("debug state is only coherent at a stopped VM")
        registers = self.gdb.read_registers()
        stack_address = ((registers["ss"] & 0xFFFF) << 4) + (registers["esp"] & 0xFFFF)
        return {
            "registers": registers,
            "linear_ip": self._linear_ip(registers),
            "image_ip": self._linear_ip(registers) - (self.runtime_image_base or 0),
            "stack_address": stack_address,
            "stack_hex": self.gdb.read_memory(stack_address, stack_bytes).hex(),
            "breakpoints": [
                {"address": address, "image_offset": address - (self.runtime_image_base or 0), "reason": reason}
                for address, reason in sorted(self.breakpoints.items())
            ],
        }

    def capture_cycle(self) -> Path:
        path = self.capture_dir / f"cycle_{self.cycle:08d}.png"
        self.qmp.screenshot(path, "png")
        metadata = {
            "cycle": self.cycle,
            "state_revision": self.state_revision,
            "stop_reason": self.current_stop.reason if self.current_stop else None,
            "room": self.cached_state.get("room"),
            "score": self.cached_state.get("score"),
            "file": path.name,
        }
        self.capture_dir.mkdir(parents=True, exist_ok=True)
        with (self.capture_dir / "captures.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(metadata, sort_keys=True) + "\n")
        return path

    def detect_dialog(self) -> dict[str, Any]:
        path = self.capture_dir / "dialog_probe.ppm"
        self.qmp.screenshot(path, "ppm")
        boxes = detect_modal_borders(path.read_bytes())
        return {
            "detected": bool(boxes),
            "boxes": boxes,
            "interpreter_window_active": (
                bool(self.read_word(self.profile.window_active))
                if self.data_segment is not None and not self.qmp.query_status().get("running")
                else None
            ),
            "cycle": self.cycle,
        }

    def key_transition(self, qcode: str, down: bool, timeout: float = 2.0) -> dict[str, Any]:
        """Deliver one physical transition while the VM runs to its next hook."""
        if self.qmp.query_status().get("running"):
            raise ControllerError("explicit key transitions require a semantic stop")
        self.begin_resume()
        try:
            self.qmp.key_event(qcode, down)
        except QmpError as exc:
            if "VM not running" not in str(exc):
                raise
            self.wait_for_stop(timeout)
            raise ControllerError("VM reached the next hook before the key transition") from exc
        self.wait_for_semantic_stop(timeout)
        return self.cached_state

    def send_key_down(self, qcode: str) -> dict[str, Any]:
        return self.key_transition(qcode, True)

    def send_key_up(self, qcode: str) -> dict[str, Any]:
        return self.key_transition(qcode, False)

    def tap_key(self, qcode: str, hold_cycles: int = 1) -> dict[str, Any]:
        if hold_cycles < 1:
            raise ControllerError("hold_cycles must be at least one")
        state = self.send_key_down(qcode)
        if state.get("stop_reason") == "cycle_boundary" and hold_cycles > 1:
            state = self.run_cycles(hold_cycles - 1)
        return self.send_key_up(qcode)

    def type_text(self, text: str, inter_key_cycles: int = 1) -> dict[str, Any]:
        state = self.read_state()
        for character in text:
            qcode, shifted = qcode_for_character(character)
            if shifted:
                self.send_key_down("shift")
            state = self.tap_key(qcode, inter_key_cycles)
            if shifted:
                state = self.send_key_up("shift")
            if state.get("stop_reason") != "cycle_boundary":
                break
        return state

    def type_host_text(self, text: str, delay_ms: float = 40.0) -> dict[str, Any]:
        """Type while uninstrumented or running, using bounded host-time delays.

        This is intentionally a bootstrap facility for DOS and loader prompts.
        Cycle-relative ``type_text`` is used after interpreter discovery.
        """
        if delay_ms < 1 or delay_ms > 1000:
            raise ControllerError("delay_ms must be between 1 and 1000")
        for character in text:
            qcode, shifted = qcode_for_character(character)
            if shifted:
                self.qmp.key_event("shift", True)
            self.qmp.key_event(qcode, True)
            time.sleep(delay_ms / 2000.0)
            self.qmp.key_event(qcode, False)
            if shifted:
                self.qmp.key_event("shift", False)
            time.sleep(delay_ms / 2000.0)
        return {"sent": len(text), "vm": self.qmp.query_status()}

    def dismiss_dialog(self, key: str = "ret", timeout: float = 10.0) -> dict[str, Any]:
        if self.current_stop is None or self.current_stop.reason != "modal_wait":
            raise ControllerError("controller is not stopped at a modal wait hook")
        self.select_breakpoints(["cycle_boundary"])
        return self.tap_key(key)

    def submit_string(self, text: str, timeout: float = 10.0) -> dict[str, Any]:
        if self.current_stop is None or self.current_stop.reason != "string_prompt_wait":
            raise ControllerError("controller is not stopped at a string prompt hook")
        state = self.cached_state
        for character in text:
            qcode, shifted = qcode_for_character(character)
            if shifted:
                self.send_key_down("shift")
            state = self.tap_key(qcode)
            if shifted:
                state = self.send_key_up("shift")
            if state.get("stop_reason") != "string_prompt_wait":
                break
        if state.get("stop_reason") == "string_prompt_wait":
            self.select_breakpoints(["cycle_boundary"])
            state = self.tap_key("ret")
        return state

    def move_until(
        self,
        direction: str,
        predicate: dict[str, Any],
        max_cycles: int,
    ) -> dict[str, Any]:
        qcodes = {"left": "left", "right": "right", "up": "up", "down": "down"}
        if direction not in qcodes:
            raise ControllerError("direction must be left, right, up, or down")
        self.tap_key(qcodes[direction])
        result = self.run_until(predicate, max_cycles)
        if result.get("stop_reason") == "cycle_boundary":
            self.tap_key("kp_5")
        return result

    def checkpoint(self, name: str) -> dict[str, Any]:
        if not name or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for character in name):
            raise ControllerError("checkpoint name must be alphanumeric with _ or -")
        self.qmp.stop()
        output = self.qmp.hmp(f"savevm {name}")
        if "Error" in output or "failed" in output.lower():
            raise ControllerError(output.strip())
        return {"checkpoint": name, "cycle": self.cycle, "output": output.strip()}

    def restore_checkpoint(self, name: str) -> dict[str, Any]:
        self.qmp.stop()
        output = self.qmp.hmp(f"loadvm {name}")
        if "Error" in output or "failed" in output.lower():
            raise ControllerError(output.strip())
        self.current_stop = None
        packet = self.gdb.query_stop()
        self.current_stop = self._decode_stop(packet)
        self.state_revision += 1
        self.cached_state = self.read_state()
        return {"checkpoint": name, "restored": True, "output": output.strip()}


class QemuProcess:
    def __init__(
        self,
        *,
        disk: Path,
        runtime_dir: Path,
        display: str,
        memory_mib: int = 16,
    ):
        runtime_dir.mkdir(parents=True, exist_ok=True)
        self.qmp_socket = runtime_dir / "qmp.sock"
        self.gdb_socket = runtime_dir / "gdb.sock"
        self.log_path = runtime_dir / "qemu.log"
        self.qmp_socket.unlink(missing_ok=True)
        self.gdb_socket.unlink(missing_ok=True)
        self.log_stream = self.log_path.open("wb")
        command = [
            "qemu-system-i386",
            "-m", str(memory_mib),
            "-boot", "c",
            "-drive", f"file={disk.resolve()},format=qcow2,if=ide,index=0,media=disk",
            *qemu_vga_args(),
            "-display", display,
            "-qmp", f"unix:{self.qmp_socket.resolve()},server=on,wait=off",
            "-gdb", f"unix:{self.gdb_socket.resolve()},server=on,wait=off",
            "-S",
        ]
        self.command = command
        self.proc = subprocess.Popen(command, stdout=self.log_stream, stderr=subprocess.STDOUT)
        self._wait_for_socket(self.qmp_socket)
        self._wait_for_socket(self.gdb_socket)

    def _wait_for_socket(self, path: Path, timeout: float = 10.0) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.proc.poll() is not None:
                raise ControllerError(f"QEMU exited with {self.proc.returncode}; see {self.log_path}")
            if path.exists():
                return
            time.sleep(0.02)
        raise ControllerError(f"QEMU socket did not appear: {path}")

    def close(self) -> None:
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=5)
        self.log_stream.close()


class ControllerApi:
    def __init__(self, session: InterpreterSession, qemu: QemuProcess):
        self.session = session
        self.qemu = qemu

    def dispatch(self, method: str, path: str, body: dict[str, Any], query: dict[str, list[str]]) -> tuple[int, str, bytes]:
        session = self.session
        if method == "GET" and path == "/v1/health":
            return self.json_response({"ok": True, "vm": session.qmp.query_status()})
        if method == "GET" and path == "/v1/state":
            return self.json_response(session.read_state())
        if method == "GET" and path == "/v1/variables":
            return self.json_response({"cycle": session.cycle, "variables": session.read_variables()})
        if method == "GET" and path == "/v1/flags":
            return self.json_response({"cycle": session.cycle, "flags": session.read_flags()})
        if method == "GET" and path == "/v1/objects":
            return self.json_response({"cycle": session.cycle, "objects": session.read_objects()})
        if method == "GET" and path == "/v1/inventory":
            return self.json_response({"cycle": session.cycle, "inventory": session.read_inventory()})
        if method == "GET" and path == "/v1/logics":
            return self.json_response({"cycle": session.cycle, "logics": session.read_logics()})
        if method == "GET" and path in ("/v1/picture/priority.ppm", "/v1/picture/visual.ppm"):
            channel = "priority" if "priority" in path else "visual"
            ppm = colorize_logical_buffer(session.read_logical_buffer(), channel)
            return 200, "image/x-portable-pixmap", ppm
        if method == "GET" and path in ("/v1/screenshot.ppm", "/v1/screenshot.png"):
            image_format = "png" if path.endswith("png") else "ppm"
            output = session.capture_dir / f"api_screenshot.{image_format}"
            session.qmp.screenshot(output, image_format)
            content_type = "image/png" if image_format == "png" else "image/x-portable-pixmap"
            return 200, content_type, output.read_bytes()
        if method == "GET" and path == "/v1/dialog":
            return self.json_response(session.detect_dialog())
        if method == "GET" and path == "/v1/debug":
            return self.json_response(
                session.read_debug_state(int(query.get("stack_bytes", ["64"])[0]))
            )

        if method == "POST" and path == "/v1/vm/continue":
            session.qmp.cont()
            return self.json_response({"vm": session.qmp.query_status()})
        if method == "POST" and path == "/v1/vm/stop":
            return self.json_response(session.pause())
        if method == "POST" and path == "/v1/vm/quit":
            session.qmp.execute("quit")
            return self.json_response({"quitting": True})
        if method == "POST" and path == "/v1/instrument/discover":
            return self.json_response(session.discover(bool(body.get("wait_for_hook", True))))
        if method == "POST" and path == "/v1/debug/breakpoints":
            return self.json_response(session.select_breakpoints(list(body.get("reasons", []))))
        if method == "POST" and path == "/v1/run/resume":
            return self.json_response(session.resume())
        if method == "POST" and path == "/v1/run/wait":
            return self.json_response(session.wait(float(body.get("timeout", 2.0))))
        if method == "POST" and path == "/v1/cycles/step":
            return self.json_response(session.step_cycle(float(body.get("timeout", 2.0))))
        if method == "POST" and path == "/v1/cycles/run":
            return self.json_response(
                session.run_cycles(int(body.get("count", 1)), float(body.get("timeout", 2.0)))
            )
        if method == "POST" and path == "/v1/cycles/run-until":
            return self.json_response(
                session.run_until(
                    body["predicate"],
                    int(body.get("max_cycles", 1000)),
                    float(body.get("timeout", 2.0)),
                )
            )
        if method == "POST" and path == "/v1/input":
            action = body.get("action", "tap")
            if action == "down":
                return self.json_response(session.send_key_down(str(body["key"])))
            if action == "up":
                return self.json_response(session.send_key_up(str(body["key"])))
            if action == "tap":
                return self.json_response(
                    session.tap_key(str(body["key"]), int(body.get("hold_cycles", 1)))
                )
            if action == "type":
                return self.json_response(
                    session.type_text(str(body.get("text", "")), int(body.get("inter_key_cycles", 1)))
                )
            if action == "host_type":
                return self.json_response(
                    session.type_host_text(str(body.get("text", "")), float(body.get("delay_ms", 40.0)))
                )
            raise ControllerError(f"unsupported input action: {action}")
        if method == "POST" and path == "/v1/dialog/dismiss":
            return self.json_response(session.dismiss_dialog(str(body.get("key", "ret"))))
        if method == "POST" and path == "/v1/string-prompt/submit":
            return self.json_response(session.submit_string(str(body.get("text", ""))))
        if method == "POST" and path == "/v1/movement/run-until":
            return self.json_response(
                session.move_until(
                    str(body["direction"]),
                    body["predicate"],
                    int(body.get("max_cycles", 1000)),
                )
            )
        if method == "POST" and path == "/v1/checkpoints":
            return self.json_response(session.checkpoint(str(body["name"])))
        if method == "POST" and path == "/v1/checkpoints/restore":
            return self.json_response(session.restore_checkpoint(str(body["name"])))
        return self.json_response({"error": "not_found", "path": path}, status=404)

    @staticmethod
    def json_response(value: Any, status: int = 200) -> tuple[int, str, bytes]:
        return status, "application/json", json.dumps(value, indent=2, sort_keys=True).encode() + b"\n"


def make_handler(api: ControllerApi) -> type[http.server.BaseHTTPRequestHandler]:
    class Handler(http.server.BaseHTTPRequestHandler):
        server_version = "AGIInterpreterController/1"

        def do_GET(self) -> None:  # noqa: N802
            self.handle_request("GET")

        def do_POST(self) -> None:  # noqa: N802
            self.handle_request("POST")

        def handle_request(self, method: str) -> None:
            parsed = urlparse(self.path)
            body: dict[str, Any] = {}
            if method == "POST":
                length = int(self.headers.get("Content-Length", "0"))
                if length:
                    try:
                        body = json.loads(self.rfile.read(length))
                    except json.JSONDecodeError as exc:
                        self.send_payload(400, "application/json", json.dumps({"error": str(exc)}).encode())
                        return
            try:
                with api.session.lock:
                    status, content_type, payload = api.dispatch(
                        method,
                        parsed.path,
                        body,
                        parse_qs(parsed.query),
                    )
            except (ControllerError, QmpError, GdbRemoteError, KeyError, ValueError, socket.timeout) as exc:
                status, content_type, payload = ControllerApi.json_response(
                    {"error": type(exc).__name__, "message": str(exc)},
                    status=409,
                )
            self.send_payload(status, content_type, payload)
            if method == "POST" and parsed.path == "/v1/vm/quit" and status == 200:
                # BaseServer.shutdown must run outside the serve_forever thread.
                threading.Thread(target=self.server.shutdown, daemon=True).start()

        def send_payload(self, status: int, content_type: str, payload: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: Any) -> None:
            print(f"api {self.address_string()} {format % args}")

    return Handler


def wait_for_client(path: Path, factory: Any, timeout: float = 10.0) -> Any:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            return factory(path)
        except (FileNotFoundError, ConnectionRefusedError, socket.error) as exc:
            last_error = exc
            time.sleep(0.02)
    raise ControllerError(f"could not connect to {path}: {last_error}")


def serve(args: argparse.Namespace) -> int:
    profile = PROFILES[args.profile]
    game_dir = args.game_dir.resolve()
    image = validate_profile(game_dir, profile)
    runtime_dir = args.runtime_dir.resolve()
    qemu = QemuProcess(
        disk=args.disk.resolve(),
        runtime_dir=runtime_dir,
        display=args.display,
        memory_mib=args.memory,
    )
    qmp: QmpClient | None = None
    gdb: GdbRemoteClient | None = None
    try:
        qmp = wait_for_client(qemu.qmp_socket, QmpClient)
        gdb = wait_for_client(qemu.gdb_socket, GdbRemoteClient)
        session = InterpreterSession(
            profile=profile,
            image=image,
            qmp=qmp,
            gdb=gdb,
            capture_dir=args.capture_dir.resolve(),
            capture_every_cycle=args.capture_every_cycle,
        )
        api = ControllerApi(session, qemu)
        server = http.server.ThreadingHTTPServer((args.host, args.port), make_handler(api))
        print(f"interpreter controller: http://{args.host}:{args.port}")
        print(f"QEMU command: {' '.join(qemu.command)}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
        return 0
    finally:
        if gdb is not None:
            gdb.close()
        if qmp is not None:
            qmp.close()
        qemu.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_parser = subparsers.add_parser("prepare", help="build a disposable qcow2 play disk")
    prepare_parser.add_argument("--base-image", type=Path, required=True)
    prepare_parser.add_argument("--game-dir", type=Path, required=True)
    prepare_parser.add_argument("--dos-game-dir", required=True)
    prepare_parser.add_argument("--raw-output", type=Path, required=True)
    prepare_parser.add_argument("--output", type=Path, required=True)

    serve_parser = subparsers.add_parser("serve", help="launch QEMU and serve the controller API")
    serve_parser.add_argument("--disk", type=Path, required=True)
    serve_parser.add_argument("--game-dir", type=Path, required=True)
    serve_parser.add_argument("--profile", choices=sorted(PROFILES), default=SQ122_PROFILE.name)
    serve_parser.add_argument("--runtime-dir", type=Path, default=Path("build/interpreter-controller/runtime"))
    serve_parser.add_argument("--capture-dir", type=Path, default=Path("build/interpreter-controller/captures"))
    serve_parser.add_argument("--capture-every-cycle", action="store_true")
    serve_parser.add_argument("--display", default="cocoa,zoom-to-fit=on")
    serve_parser.add_argument("--memory", type=int, default=16)
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8765)

    args = parser.parse_args()
    if args.command == "prepare":
        output = prepare_session_disk(
            base_image=args.base_image.resolve(),
            game_dir=args.game_dir.resolve(),
            dos_game_dir=args.dos_game_dir,
            raw_output=args.raw_output.resolve(),
            qcow_output=args.output.resolve(),
        )
        print(output)
        return 0
    return serve(args)


if __name__ == "__main__":
    raise SystemExit(main())
