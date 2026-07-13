#!/usr/bin/env python3
"""Tests for the persistent interpreter-controller state and image helpers."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from interpreter_controller import (  # noqa: E402
    ControllerError,
    InterpreterSession,
    SQ122_PROFILE,
    adapter_for_profile,
    classify_blocking_stack,
    colorize_logical_buffer,
    compress_cardinal_path,
    detect_modal_borders,
    dialog_fingerprint,
    evaluate_predicate,
    find_runtime_image_base,
    parse_object_records,
    parse_ppm,
    plan_priority_path,
    qcode_for_character,
    state_delta,
    summarize_state,
    unpack_flags,
)


class FakeMemoryGdb:
    def __init__(self, memory: bytes):
        self.memory = memory

    def read_memory(self, address: int, size: int, chunk_size: int = 0x1000) -> bytes:
        return self.memory[address : address + size]


class MovementControllerStub:
    """Exercise move_until without starting QEMU or opening sockets."""

    def __init__(self, direction: int):
        self.direction = direction
        self.tapped: list[str] = []

    def read_state(self) -> dict:
        return {
            "cycle": 1,
            "room": 1,
            "objects": [{"direction": self.direction, "x": 10, "y": 20}],
        }

    def _adapter(self):
        return adapter_for_profile(SQ122_PROFILE)

    def tap_key(self, key: str) -> dict:
        self.tapped.append(key)
        return {**self.read_state(), "input_delivery": {"status": "delivered"}}

    def run_until_guarded(
        self,
        predicate: dict,
        max_cycles: int,
        **kwargs: object,
    ) -> dict:
        return {
            **self.read_state(),
            "stop_reason": "modal_wait",
            "guard_status": "semantic_interruption",
            "matched": False,
            "cycles_run": 1,
        }

    def stop_movement(self) -> dict:
        self.direction = 0
        return {**self.read_state(), "movement_stop": {"status": "stopped"}}


class FakeQmp:
    def __init__(self, transitions: list[str] | None = None):
        self.transitions = list(transitions or [])

    def query_status(self) -> dict:
        return {"running": False, "status": "paused"}

    def key_event(self, qcode: str, down: bool) -> None:
        outcome = self.transitions.pop(0) if self.transitions else "ok"
        if outcome == "race":
            from interpreter_controller import QmpError

            raise QmpError("input-send-event: GenericError: VM not running")

    def screenshot(self, path: Path, image_format: str = "ppm") -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"deterministic-screen")
        return path


class FakeGdb:
    pass


class GuardedControllerStub:
    _named_predicates = staticmethod(InterpreterSession._named_predicates)

    def __init__(self, states: list[dict]):
        self.states = states
        self.index = 0

    def read_state(self) -> dict:
        return self.states[self.index]

    def step_cycle(self, timeout: float) -> dict:
        self.index += 1
        return self.states[self.index]


class WaypointControllerStub:
    def __init__(self):
        self.state = {
            "cycle": 0,
            "room": 4,
            "objects": [{"x": 10, "y": 10, "direction": 0}],
        }
        self.moves: list[tuple[str, str, str, int]] = []

    def read_state(self) -> dict:
        return self.state

    def move_until(
        self,
        direction: str,
        predicate: dict,
        max_cycles: int,
        **kwargs: object,
    ) -> dict:
        axis = predicate["path"].split(".")[-1]
        target = int(predicate["value"])
        self.state["objects"][0][axis] = target
        self.moves.append((direction, axis, predicate["op"], target))
        return {
            **self.state,
            "movement": {"target_matched": True, "status": "target_matched"},
        }


class InterpreterControllerTests(unittest.TestCase):
    def test_move_until_preserves_matching_active_direction(self) -> None:
        from interpreter_controller import InterpreterSession

        stub = MovementControllerStub(direction=7)
        InterpreterSession.move_until(stub, "left", {"path": "room", "value": 1}, 20)
        self.assertEqual(stub.tapped, [])

    def test_move_until_selects_different_direction(self) -> None:
        from interpreter_controller import InterpreterSession

        stub = MovementControllerStub(direction=0)
        InterpreterSession.move_until(stub, "left", {"path": "room", "value": 1}, 20)
        self.assertEqual(stub.tapped, ["left"])

    def test_unpack_flags_uses_high_bit_first(self) -> None:
        flags = unpack_flags(bytes([0xA1]))
        self.assertEqual(flags, [True, False, True, False, False, False, False, True])

    def test_parse_object_records_exposes_semantic_fields(self) -> None:
        record = bytearray(43)
        record[3:5] = (126).to_bytes(2, "little")
        record[5:7] = (108).to_bytes(2, "little")
        record[7] = 9
        record[0x0A] = 2
        record[0x0E] = 6
        record[0x1A:0x1C] = (14).to_bytes(2, "little")
        record[0x1C:0x1E] = (20).to_bytes(2, "little")
        record[0x21] = 7
        record[0x22] = 3
        record[0x25:0x27] = (0x1234).to_bytes(2, "little")
        parsed = parse_object_records(bytes(record), 0x42F3)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["x"], 126)
        self.assertEqual(parsed[0]["y"], 108)
        self.assertEqual(parsed[0]["view"], 9)
        self.assertEqual(parsed[0]["direction"], 7)
        self.assertEqual(parsed[0]["motion_mode"], 3)
        self.assertEqual(parsed[0]["flags"], 0x1234)

    def test_parse_object_records_rejects_partial_record(self) -> None:
        with self.assertRaises(ControllerError):
            parse_object_records(bytes(42), 0)

    def test_parse_object_records_rejects_unimplemented_layout(self) -> None:
        with self.assertRaisesRegex(ControllerError, "no object-record decoder"):
            parse_object_records(bytes(44), 0, record_size=44)

    def test_colorize_priority_uses_high_nibble(self) -> None:
        ppm = colorize_logical_buffer(bytes([0x4E]), "priority", width=1, height=1)
        width, height, pixels = parse_ppm(ppm)
        self.assertEqual((width, height), (1, 1))
        self.assertEqual(pixels, bytes((0xAA, 0x00, 0x00)))

    def test_colorize_visual_uses_low_nibble(self) -> None:
        ppm = colorize_logical_buffer(bytes([0x4E]), "visual", width=1, height=1)
        _, _, pixels = parse_ppm(ppm)
        self.assertEqual(pixels, bytes((0xFF, 0xFF, 0x55)))

    def test_modal_detector_finds_red_box_with_white_interior(self) -> None:
        width, height = 120, 80
        pixels = bytearray((0, 0, 0) * width * height)

        def set_pixel(x: int, y: int, color: tuple[int, int, int]) -> None:
            offset = (y * width + x) * 3
            pixels[offset : offset + 3] = bytes(color)

        for y in range(20, 61):
            for x in range(15, 106):
                set_pixel(x, y, (255, 255, 255))
        for x in range(15, 106):
            set_pixel(x, 20, (168, 0, 0))
            set_pixel(x, 60, (168, 0, 0))
        for y in range(20, 61):
            set_pixel(15, y, (168, 0, 0))
            set_pixel(105, y, (168, 0, 0))
        ppm = f"P6\n{width} {height}\n255\n".encode() + bytes(pixels)
        self.assertEqual(
            detect_modal_borders(ppm),
            [{"left": 15, "top": 20, "right": 105, "bottom": 60}],
        )

    def test_modal_detector_rejects_plain_screen(self) -> None:
        ppm = b"P6\n40 30\n255\n" + bytes((0, 0, 0) * 40 * 30)
        self.assertEqual(detect_modal_borders(ppm), [])

    def test_dialog_identity_ignores_pixels_outside_the_dialog(self) -> None:
        width, height = 8, 6
        box = {"left": 2, "top": 1, "right": 5, "bottom": 4}

        def image(background: tuple[int, int, int]) -> bytes:
            pixels = bytearray(background * (width * height))
            for y in range(box["top"], box["bottom"] + 1):
                for x in range(box["left"], box["right"] + 1):
                    offset = (y * width + x) * 3
                    pixels[offset : offset + 3] = bytes((255, 255, 255))
            return f"P6\n{width} {height}\n255\n".encode() + bytes(pixels)

        first = dialog_fingerprint(image((0, 0, 0)), [box])
        second = dialog_fingerprint(image((0, 170, 0)), [box])
        self.assertEqual(first, second)

    def test_nested_predicate(self) -> None:
        state = {"room": 1, "objects": [{"x": 126, "y": 108}], "flags": [False, True]}
        predicate = {
            "all": [
                {"path": "room", "op": "eq", "value": 1},
                {"path": "objects.0.x", "op": "between", "value": [98, 130]},
                {"path": "flags.1", "op": "truthy"},
            ]
        }
        self.assertTrue(evaluate_predicate(state, predicate))

    def test_predicate_supports_recursive_not(self) -> None:
        state = {"room": 3}
        self.assertTrue(
            evaluate_predicate(
                state,
                {"not": {"path": "room", "op": "eq", "value": 4}},
            )
        )

    def test_predicate_reports_malformed_operator_value(self) -> None:
        with self.assertRaisesRegex(ControllerError, "invalid value"):
            evaluate_predicate(
                {"room": 3},
                {"path": "room", "op": "between", "value": [1]},
            )

    def test_state_delta_reports_semantic_changes(self) -> None:
        before = {
            "cycle": 2,
            "score": 7,
            "variables": [1, 7],
            "flags": [False, True],
            "objects": [{"x": 10, "y": 20, "direction": 0}],
        }
        after = {
            "cycle": 3,
            "score": 9,
            "variables": [1, 9],
            "flags": [True, True],
            "objects": [{"x": 12, "y": 20, "direction": 3}],
        }
        delta = state_delta(before, after)
        self.assertEqual(delta["scalars"]["score"], {"before": 7, "after": 9})
        self.assertEqual(delta["variables"], [{"index": 1, "before": 7, "after": 9}])
        self.assertEqual(delta["flags"], [{"index": 0, "before": False, "after": True}])
        self.assertEqual(delta["objects"][0]["fields"]["x"]["after"], 12)

    def test_state_summary_includes_current_logic_and_ego(self) -> None:
        summary = summarize_state(
            {
                "cycle": 8,
                "room": 6,
                "current_logic": 103,
                "current_logic_resume_ip": 42,
                "objects": [{"x": 100, "y": 130, "direction": 0}],
                "variables": list(range(10)),
            }
        )
        self.assertEqual(summary["current_logic"], 103)
        self.assertEqual(summary["ego"]["x"], 100)
        self.assertNotIn("variables", summary)

    def test_priority_path_routes_through_control_gap(self) -> None:
        width, height = 7, 5
        logical = bytearray([0x40] * (width * height))
        for y in range(height):
            if y != 2:
                logical[y * width + 3] = 0x00
        plan = plan_priority_path(
            bytes(logical),
            width=width,
            height=height,
            start=(1, 1),
            goal=(5, 1),
        )
        self.assertIn({"x": 3, "y": 2}, plan["path"])
        self.assertEqual(plan["reached_goal"], {"x": 5, "y": 1})
        self.assertGreaterEqual(len(plan["waypoints"]), 3)

    def test_priority_path_respects_ego_footprint(self) -> None:
        logical = bytes([0x40, 0x40, 0x00, 0x40, 0x40])
        with self.assertRaisesRegex(ControllerError, "goal baseline footprint is blocked"):
            plan_priority_path(
                logical,
                width=5,
                height=1,
                start=(0, 0),
                goal=(1, 0),
                footprint_width=2,
            )

    def test_cardinal_path_compresses_to_turns(self) -> None:
        self.assertEqual(
            compress_cardinal_path([(0, 0), (1, 0), (2, 0), (2, 1), (2, 2)]),
            [{"x": 2, "y": 0}, {"x": 2, "y": 2}],
        )

    def test_guarded_wait_aborts_when_invariant_fails(self) -> None:
        stub = GuardedControllerStub(
            [
                {"room": 1, "score": 0, "stop_reason": "cycle_boundary"},
                {"room": 2, "score": 0, "stop_reason": "cycle_boundary"},
            ]
        )
        result = InterpreterSession.run_until_guarded(
            stub,
            {"path": "score", "op": "eq", "value": 5},
            10,
            invariants=[
                {
                    "name": "stay_in_room",
                    "predicate": {"path": "room", "op": "eq", "value": 1},
                }
            ],
        )
        self.assertEqual(result["guard_status"], "invariant_failed")
        self.assertEqual(result["failed_guard"], "stay_in_room")

    def test_waypoint_movement_uses_explicit_axis_order(self) -> None:
        stub = WaypointControllerStub()
        result = InterpreterSession.move_waypoints(
            stub,
            [{"x": 20, "y": 30, "axis_order": "y_then_x"}],
        )
        self.assertEqual(
            stub.moves,
            [("down", "y", "ge", 30), ("right", "x", "ge", 20)],
        )
        self.assertEqual(result["waypoint_movement"]["status"], "completed")

    def test_waypoint_movement_uses_crossing_predicate_when_decreasing(self) -> None:
        stub = WaypointControllerStub()
        InterpreterSession.move_waypoints(stub, [{"x": 5}])
        self.assertEqual(stub.moves, [("left", "x", "le", 5)])

    def test_keyboard_character_mapping(self) -> None:
        self.assertEqual(qcode_for_character("a"), ("a", False))
        self.assertEqual(qcode_for_character("A"), ("a", True))
        self.assertEqual(qcode_for_character(":"), ("semicolon", True))
        self.assertEqual(qcode_for_character("\n"), ("ret", False))

    def test_blocking_stack_classifies_shared_string_editor(self) -> None:
        stack = b"\x00\x00" * 4 + (0x0DF8).to_bytes(2, "little") + b"\x00\x00"
        self.assertEqual(classify_blocking_stack(stack, SQ122_PROFILE), "string_prompt_wait")

    def test_blocking_stack_classifies_modal_message_wait(self) -> None:
        stack = b"\x00\x00" * 3 + (0x1D25).to_bytes(2, "little")
        self.assertEqual(classify_blocking_stack(stack, SQ122_PROFILE), "modal_wait")

    def test_sq122_profile_uses_verified_cycle_and_ui_hooks(self) -> None:
        self.assertEqual(SQ122_PROFILE.cycle_boundary, 0x015B)
        self.assertEqual(SQ122_PROFILE.string_prompt_wait, 0x0DF2)
        self.assertEqual(SQ122_PROFILE.string_prompt_wait_return, 0x0DF8)
        self.assertEqual(SQ122_PROFILE.modal_wait, 0x1D1B)
        self.assertEqual(SQ122_PROFILE.modal_wait_return, 0x1D25)

    def test_sq122_profile_has_explicit_state_adapter(self) -> None:
        adapter = adapter_for_profile(SQ122_PROFILE)
        self.assertEqual(type(adapter).__name__, "SQ122Adapter")
        self.assertIs(adapter.profile, SQ122_PROFILE)
        self.assertEqual(adapter.movement_control("left"), ("left", 7))
        self.assertEqual(adapter.movement_stop_key(), "kp_5")
        self.assertEqual(adapter.default_blocked_priorities(), {0, 1})

    def test_release_race_becomes_pending_state_not_exception(self) -> None:
        session = InterpreterSession(
            profile=SQ122_PROFILE,
            image=b"",
            qmp=FakeQmp(["race"]),
            gdb=FakeGdb(),
            capture_dir=Path("build/test-controller"),
        )
        session.cached_state = {
            "cycle": 12,
            "stop_reason": "cycle_boundary",
            "objects": [{"direction": 0}],
        }
        session.held_keys.add("ret")
        session.begin_resume = lambda: None  # type: ignore[method-assign]
        session.wait_for_stop = lambda timeout=None: None  # type: ignore[method-assign]
        result = session.send_key_up("ret")
        self.assertEqual(result["input_delivery"]["status"], "release_pending")
        self.assertEqual(result["input_delivery"]["pending_releases"], ["ret"])
        self.assertIn("ret", session.held_keys)

    def test_pending_release_reconciles_on_later_window(self) -> None:
        session = InterpreterSession(
            profile=SQ122_PROFILE,
            image=b"",
            qmp=FakeQmp(["race", "ok"]),
            gdb=FakeGdb(),
            capture_dir=Path("build/test-controller"),
        )
        session.cached_state = {
            "cycle": 12,
            "stop_reason": "cycle_boundary",
            "objects": [{"direction": 0}],
        }
        session.held_keys.add("ret")
        session.begin_resume = lambda: None  # type: ignore[method-assign]
        session.wait_for_stop = lambda timeout=None: None  # type: ignore[method-assign]
        session.wait_for_semantic_stop = lambda timeout=2.0: None  # type: ignore[method-assign]
        session.send_key_up("ret")
        result = session.reconcile_pending_keys(max_attempts=2)
        self.assertEqual(result["reconciliation"]["status"], "reconciled")
        self.assertEqual(session.held_keys, set())

    def test_transaction_is_postcondition_driven_and_idempotent(self) -> None:
        session = InterpreterSession(
            profile=SQ122_PROFILE,
            image=b"",
            qmp=FakeQmp(),
            gdb=FakeGdb(),
            capture_dir=Path("build/test-controller"),
        )
        state = {
            "cycle": 4,
            "state_revision": 4,
            "stop_reason": "cycle_boundary",
            "room": 1,
            "score": 0,
            "variables": [1, 0, 0, 0],
            "flags": [False],
            "objects": [{"x": 10, "y": 20, "direction": 0}],
        }
        calls = []
        session.read_state = lambda: state  # type: ignore[method-assign]

        def perform(action: dict) -> dict:
            calls.append(action)
            state["score"] = 2
            state["variables"][3] = 2
            return state

        session.perform_semantic_action = perform  # type: ignore[method-assign]
        spec = {
            "idempotency_key": "scientist-award",
            "precondition": {"path": "room", "op": "eq", "value": 1},
            "action": {"type": "command", "text": "look scientist"},
            "postcondition": {"path": "score", "op": "eq", "value": 2},
        }
        first = session.execute_transaction(spec)
        second = session.execute_transaction(spec)
        self.assertEqual(first["status"], "succeeded")
        self.assertEqual(first["outcome_certainty"], "observed_postcondition")
        self.assertEqual(
            first["delta"]["scalars"]["score"],
            {"before": 0, "after": 2},
        )
        self.assertEqual(first["trace"][-1]["kind"], "transaction_finished")
        self.assertTrue(second["idempotent_replay"])
        self.assertEqual(len(calls), 1)

    def test_transaction_does_not_act_when_precondition_fails(self) -> None:
        session = InterpreterSession(
            profile=SQ122_PROFILE,
            image=b"",
            qmp=FakeQmp(),
            gdb=FakeGdb(),
            capture_dir=Path("build/test-controller"),
        )
        state = {
            "cycle": 1,
            "state_revision": 1,
            "stop_reason": "cycle_boundary",
            "room": 2,
            "objects": [{"x": 0, "y": 0, "direction": 0}],
        }
        session.read_state = lambda: state  # type: ignore[method-assign]
        session.perform_semantic_action = (  # type: ignore[method-assign]
            lambda action: self.fail("action ran despite failed precondition")
        )
        result = session.execute_transaction(
            {
                "precondition": {"path": "room", "op": "eq", "value": 1},
                "action": {"type": "tap", "key": "ret"},
            }
        )
        self.assertEqual(result["status"], "precondition_failed")
        self.assertEqual(result["condition_evaluations"]["precondition"], False)

    def test_transaction_accepts_achieved_postcondition_before_precondition(self) -> None:
        session = InterpreterSession(
            profile=SQ122_PROFILE,
            image=b"",
            qmp=FakeQmp(),
            gdb=FakeGdb(),
            capture_dir=Path("build/test-controller"),
        )
        state = {
            "cycle": 3,
            "state_revision": 7,
            "stop_reason": "cycle_boundary",
            "room": 2,
            "objects": [{"x": 97, "y": 44, "direction": 0}],
        }
        session.read_state = lambda: state  # type: ignore[method-assign]
        session.perform_semantic_action = (  # type: ignore[method-assign]
            lambda action: self.fail("action ran despite achieved postcondition")
        )
        result = session.execute_transaction(
            {
                "precondition": {
                    "path": "stop_reason",
                    "op": "eq",
                    "value": "string_prompt_wait",
                },
                "action": {"type": "submit_string", "text": "x"},
                "postcondition": {
                    "path": "stop_reason",
                    "op": "eq",
                    "value": "cycle_boundary",
                },
            }
        )
        self.assertEqual(result["status"], "already_satisfied")
        self.assertEqual(result["outcome_certainty"], "observed_postcondition")

    def test_transaction_rejects_same_key_with_different_action(self) -> None:
        session = InterpreterSession(
            profile=SQ122_PROFILE,
            image=b"",
            qmp=FakeQmp(),
            gdb=FakeGdb(),
            capture_dir=Path("build/test-controller"),
        )
        state = {
            "cycle": 1,
            "state_revision": 1,
            "stop_reason": "cycle_boundary",
            "room": 1,
            "objects": [{"x": 0, "y": 0, "direction": 0}],
        }
        session.read_state = lambda: state  # type: ignore[method-assign]
        session.perform_semantic_action = lambda action: state  # type: ignore[method-assign]
        session.execute_transaction(
            {"idempotency_key": "same", "action": {"type": "noop"}}
        )
        conflict = session.execute_transaction(
            {"idempotency_key": "same", "action": {"type": "tap", "key": "ret"}}
        )
        self.assertEqual(conflict["status"], "idempotency_conflict")

    def test_cycle_capture_bundles_state_trace_and_screenshot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            session = InterpreterSession(
                profile=SQ122_PROFILE,
                image=b"",
                qmp=FakeQmp(),
                gdb=FakeGdb(),
                capture_dir=Path(temporary),
            )
            session.cycle = 9
            session.state_revision = 12
            session.cached_state = {
                "cycle": 9,
                "state_revision": 12,
                "stop_reason": "cycle_boundary",
                "room": 6,
                "score": 10,
                "variables": [6, 5, 0, 10],
                "flags": [False, True],
                "objects": [{"x": 100, "y": 130, "direction": 0}],
            }
            session.record_trace_event(
                "input_delivered",
                details={"key": "ret", "down": True},
            )
            metadata_path = session.capture_cycle()
            second_metadata_path = session.capture_cycle()
            metadata = json.loads(metadata_path.read_text())
            self.assertEqual(metadata["state"]["room"], 6)
            self.assertEqual(metadata["input_events"][0]["kind"], "input_delivered")
            self.assertTrue((metadata_path.parent / "screen.png").exists())
            self.assertNotEqual(metadata_path, second_metadata_path)
            self.assertTrue(metadata_path.exists())
            restarted = InterpreterSession(
                profile=SQ122_PROFILE,
                image=b"",
                qmp=FakeQmp(),
                gdb=FakeGdb(),
                capture_dir=Path(temporary),
            )
            restarted.cycle = session.cycle
            restarted.state_revision = session.state_revision
            restarted.cached_state = session.cached_state
            restarted_path = restarted.capture_cycle()
            self.assertIn("capture_00000003", str(restarted_path))
            manifest = Path(temporary, "cycles.jsonl").read_text().splitlines()
            self.assertEqual(len(manifest), 3)

    def test_runtime_image_discovery_uses_cycle_signature(self) -> None:
        image = bytearray(0x4000)
        image[0x150 : 0x170] = bytes(range(32))
        memory = bytearray(0xA0000)
        base = 0x23000
        memory[base : base + len(image)] = image
        discovered = find_runtime_image_base(FakeMemoryGdb(bytes(memory)), bytes(image), SQ122_PROFILE)
        self.assertEqual(discovered, base)


if __name__ == "__main__":
    unittest.main()
