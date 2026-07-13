# Interpreter Controller

`tools/interpreter_controller.py` is a persistent, localhost-only controller
for cycle-stepped runs of a private original interpreter under QEMU. It wraps
QEMU's QMP lifecycle/input/screenshot interface and its GDB remote memory and
register interface behind JSON HTTP requests. The selected game is always
explicit, and preparation copies it to a disposable disk under `build/`.
Nothing under `games/` is modified. The disposable SQ1.22 interpreter copy is
patched to initialize its shared pseudorandom generator from the fixed seed
`0x5eed` rather than the BIOS tick count.

For the static-first analysis workflow, experiment design, failure diagnosis,
and guidance on turning controller observations into a reusable state graph,
see [Developing and Validating Playthroughs](./developing_playthroughs.md).

> **Warning:** this is not yet a generic AGI controller. Only its QMP/GDB and
> HTTP orchestration layers are intended to be version-neutral. The current
> executable anchor, hooks, stack returns, DS layout, object/inventory/logic
> decoders, logical-buffer interpretation, and modal screen oracle are
> validated only for SQ1.22's AGI 2.917 build. A future profile requires fresh
> evidence for all of those assumptions, not merely a different executable
> hash.

The initial profile is limited deliberately to SQ1.22 and its observed 2.917
interpreter. Startup validates the SHA-256 of the locally decoded executable
before any offsets are used. A mismatching interpreter is rejected rather than
being treated as a compatible build.

## Runtime control model

The controller discovers the paragraph-aligned loaded executable from a
relocation-free byte signature. In the observed SQ1.22 run the executable base
was physical `0x63a0` and DS was `0x102f`. These are observations, not fixed
launch assumptions.

The normal debugger hook is image `0x015b`, at the start of each repeated
interpreter cycle. QEMU pauses before the instruction executes, the controller
reads coherent state, and an explicit API request steps off the hook and runs
to the next hook. `--capture-every-cycle` writes an immutable bundle containing
the screenshot, full state, state delta, trace events, and input transitions at
every cycle stop. `--capture-logical-buffers` also stores the visual and
priority channels from that same stop.

This QEMU real-mode GDB path honored only one execution breakpoint reliably in
the live SQ1.22 experiment. The controller therefore does not leave the cycle,
string-input, and modal hooks active simultaneously. It keeps the cycle hook
active normally. If execution does not return because the current cycle has
entered a blocking UI, the controller interrupts it and examines aligned near
return addresses on the interpreter stack:

- return `0x0df8` identifies the shared string editor reached from the visible
  edit loop at `0x0df2`;
- return `0x1d25` identifies the modal message wait reached from the visible
  loop at `0x1d1b`.

The appropriate single UI hook is then selected. Accepting a string or
dismissing a modal restores the cycle hook. This switching was confirmed with
logic 69's ordinary `0x73` string input, a normal room command that opened a
modal message, and a return to cycle control after each UI was accepted.

## Preparing and launching a session

After deleting `build/`, recreate the base image first. This also rebuilds the
derived VGA option ROM used by the controller:

```bash
python3 -B tools/setup_freedos_image.py --force
```

Then create a disposable raw clone and qcow2 play disk. The RNG patch is
generated during this command; it is not copied from an earlier build
artifact:

```bash
python3 -B tools/interpreter_controller.py prepare \
  --base-image build/freedos/freedos.img \
  --game-dir games/SQ1.22 \
  --dos-game-dir SQ122 \
  --raw-output build/interpreter-controller/session/sq122.raw \
  --output build/interpreter-controller/session/sq122.qcow2
```

Preparation validates the pristine decoded interpreter hash and the original
RNG seed instruction bytes before applying the patch. Rebuild play disks made
with an older controller; runtime discovery rejects an interpreter that does
not contain the fixed-seed instructions. The patch changes only initialization:
the original state transition and output mixing remain intact, so random
operations produce a repeatable sequence rather than one repeated value.

All four source-backed game-randomness callers use this shared generator:
approach-motion recovery, random-motion direction, random-motion duration, and
the `random_range_to_var` action used by game scripts. The other two BIOS timer
reads in the executable bound startup display-adapter detection and do not feed
the random state. Checkpoint restore naturally restores the generator state as
part of the VM snapshot. Repeating the same cycle-relative inputs from the same
checkpoint therefore repeats subsequent random outcomes.

Launch the persistent controller and visible Cocoa QEMU window:

```bash
python3 -B tools/interpreter_controller.py serve \
  --disk build/interpreter-controller/session/sq122.qcow2 \
  --game-dir games/SQ1.22 \
  --display cocoa,zoom-to-fit=on \
  --runtime-dir build/interpreter-controller/runtime \
  --capture-dir build/interpreter-controller/captures \
  --capture-every-cycle \
  --capture-logical-buffers \
  --port 8765
```

QEMU starts paused at reset. Resume it, wait for DOS, and use the bootstrap
host-time input only to launch the interpreter:

```bash
curl -X POST http://127.0.0.1:8765/v1/vm/continue -d '{}'
sleep 5
curl -X POST http://127.0.0.1:8765/v1/input \
  -H 'Content-Type: application/json' \
  -d '{"action":"host_type","text":"cd \\sq122\nsierra\n"}'
sleep 2
curl -X POST http://127.0.0.1:8765/v1/instrument/discover \
  -H 'Content-Type: application/json' \
  -d '{"wait_for_hook":true}'
```

The DOS wait remains an explicit caller responsibility because firmware and
disk startup are outside the interpreter cycle model. After discovery,
cycle-relative input methods should be used.

## Architecture and profile adapters

QMP/GDB lifecycle, transactions, traces, input reconciliation, movement, and
recording are generic controller services. Interpreter packaging and memory
semantics are owned by an explicit `InterpreterAdapter`. The current
`SQ122Adapter` is responsible for validating/decrypting its selected input,
classifying blocking stacks, decoding variables, flags, objects, inventory and
logic-cache records, interpreting the logical screen, and supplying the modal
screen oracle. It also owns the observed direction codes, movement keys, stop
key, and default blocked-priority set. `InterpreterSession` no longer contains
those profile-specific layouts or control values.

A future profile must register both an `InterpreterProfile` and an adapter. A
hash-only profile is insufficient and fails before the VM is interpreted.
`GET /v1/profile` reports the selected profile and adapter.
It also reports the controller's fixed randomness mode and seed.

## HTTP surface

All endpoints bind to `127.0.0.1` by default. Mutating requests use JSON POST
bodies; state and image requests use GET.

| Endpoint | Result |
|---|---|
| `GET /v1/state` | Full coherent state, current logic/resume context, and held/pending key state |
| `GET /v1/profile`, `/input/state`, `/trace` | Adapter identity, keyboard reconciliation state, or sequenced transition events |
| `GET /v1/variables`, `/flags`, `/objects`, `/inventory`, `/logics` | Individual state families |
| `GET /v1/picture/priority.ppm`, `/visual.ppm` | Current profile-decoded logical channels |
| `GET /v1/screenshot.ppm`, `/screenshot.png` | Current VGA output through QMP |
| `GET /v1/dialog` | Modal boxes, stable dialog ID, and interpreter-memory oracle |
| `POST /v1/cycles/step`, `/run`, `/run-until` | Basic cycle execution |
| `POST /v1/cycles/run-until-guarded` | Predicate wait with invariants and abort predicates |
| `POST /v1/input` | Down/up/tap/type, bootstrap typing, release reconciliation, or release-all |
| `POST /v1/semantic/command` | Submit one command-line string and Enter |
| `POST /v1/string-prompt/submit` | Submit shared-editor text and restore cycle control |
| `POST /v1/dialog/dismiss` | Idempotently dismiss a matching dialog instance |
| `POST /v1/semantic/direction`, `/stop-movement`, `/wait` | Direction selection, explicit stop, or named state wait |
| `POST /v1/movement/run-until`, `/waypoints` | Guarded single segment or multi-waypoint movement |
| `POST /v1/movement/plan`, `/navigate` | Plan or execute a local priority-aware path |
| `POST /v1/transactions` | Execute an idempotent state-contract action |
| `POST /v1/captures/cycle` | Write a cycle-aligned recording bundle on demand |
| `POST /v1/checkpoints`, `/checkpoints/restore` | Save/restore VM, keyboard state, and active semantic hook |
| `GET /v1/debug` | Registers, stack, image-relative IP, and active hook |
| `POST /v1/vm/quit` | Quit QEMU and shut down the server |

`GET /v1/trace` accepts `since` and `limit` query parameters. Every event has a
monotonic sequence, cycle, revision, kind, compact state, and details. Events
cover semantic stops, state deltas, requested/delivered/deferred input,
transactions, reconciliation, and checkpoints.

## Predicates, guards, and transactions

Predicates address nested fields with dotted paths. Supported operators are
`eq`, `ne`, `lt`, `le`, `gt`, `ge`, `in`, `contains`, `between`, `truthy`, and
`falsy`, with recursive `all`, `any`, and `not` forms.

`POST /v1/transactions` is the preferred mutation interface. A transaction
contains an optional precondition, one semantic action, acceptable
postconditions, invariants, a cycle bound, and an idempotency key:

```json
{
  "idempotency_key": "open-bay-once",
  "precondition": {
    "all": [
      {"path": "room", "op": "eq", "value": 6},
      {"path": "score", "op": "eq", "value": 8}
    ]
  },
  "action": {"type": "command", "text": "press open bay door"},
  "postconditions": [
    {
      "name": "door-state",
      "predicate": {"path": "variables.52", "op": "eq", "value": 1}
    },
    {
      "name": "score-award",
      "predicate": {"path": "score", "op": "eq", "value": 10}
    }
  ],
  "postcondition_mode": "all",
  "invariants": [
    {
      "name": "stay-in-room",
      "predicate": {"path": "room", "op": "eq", "value": 6}
    }
  ],
  "max_cycles": 100
}
```

The result separates `status` from `outcome_certainty`, lists every condition
evaluation, includes compact start/final states and a semantic delta, and
returns the trace slice. Reusing an idempotency key with the identical request
returns the cached result without input. Reusing it with a different request
returns `idempotency_conflict`. Restoring a checkpoint clears this cache because
the game state has moved backward. The desired postcondition is checked before
the precondition, so retrying an already-achieved operation remains a no-input
`already_satisfied` result even when the transition's original precondition no
longer holds.

Actions include `tap`, `key_down`, `key_up`, `release_all_keys`, `type_text`,
`command`, `submit_string`, `dismiss_dialog`, `select_direction`,
`stop_movement`, `move_until`, `waypoints`, `navigate_priority`,
`wait_for_state`, and `wait_for_animation`.

## Reliable input and semantic UI operations

Physical key delivery and game outcome are separate. The controller tracks
`held_keys` and `pending_releases`. If key-down completes an action and the VM
reaches its next hook before QMP accepts key-up, the response is HTTP 200 with
`input_delivery.status = release_pending`; it is not a false action failure.
The next tap first makes bounded reconciliation attempts, and callers can use
`{"action":"reconcile"}` or `{"action":"release_all"}` explicitly.

A transition that loses the race before key-down is reported as
`not_delivered`. Transactions determine success from postconditions, so a
blind retry is never required. Their `outcome_certainty` distinguishes an
observed postcondition, a deferred release, and an unverified result.

`GET /v1/dialog` hashes only the detected dialog rectangle, excluding animated
background pixels. Passing that `dialog_id` to `/v1/dialog/dismiss` makes the
operation idempotent: an absent dialog is `already_absent`, while a different
dialog is `dialog_mismatch` and receives no input.

## Guarded movement and priority planning

`movement/run-until` preserves an already-active matching direction, because
repeating it is a game-level stop toggle. It accepts invariants and positive
abort predicates, then explicitly stops movement at the target or interruption.
`movement/waypoints` composes cardinal segments with `x_then_y` or `y_then_x`
ordering, per-segment cycle limits, coordinate tolerance, and optional
initial-room preservation. Segment completion uses direction-aware crossing
predicates rather than exact equality, so a step size greater than one cannot
skip a coordinate forever.

`movement/plan` performs a breadth-first search over the live priority channel.
Acceptance tests every pixel in ego's baseline footprint, not only ego's left
coordinate. Priorities 0 and 1 are blocked by default; callers can override
the set for a room-specific hypothesis. The result contains the complete pixel
path and a compressed list of turns. `movement/navigate` executes those turns
with room preservation and the same guards.

This planner is intentionally local to the current logical screen. It does not
infer elevators, room transitions, dynamic object collision, horizons, or
room-logic control overrides. Multi-room hypotheses should be supplied as
explicit waypoint/transaction stages, and unexpected behavior should trip an
invariant rather than trigger speculative movement.

## Transition traces and cycle recordings

Every semantic stop records the compact state and a delta covering scalar
state, changed variables and flags, and changed object fields. The state also
contains the current logic-cache record and resume IP visible at the stop.
Transactions record their own predicate evaluations. This provides useful
logic context without claiming to trace every opcode or internal condition
branch inside a cycle.

Cycle recording happens while QEMU remains stopped. Each directory under
`CAPTURE_DIR/cycles/` contains `screen.png`, `cycle.json`, and optionally
`visual.ppm` and `priority.ppm`. `cycle.json` contains the full state, delta
from the previous recorded cycle, and all trace/input events since that cycle.
The controller builds each uniquely sequenced directory under a temporary name
and publishes it atomically. Only after the bundle is complete is a row
appended to `cycles.jsonl`, including the screenshot SHA-256. Capture sequence,
cycle, and state-revision numbers make image/state pairing explicit and permit
multiple immutable captures of the same semantic stop.

## SQ1.22 state mapping

The `SQ122Adapter` uses the locally verified 2.917 data layout: variables at
DS `0x0009`, packed high-bit-first flags at `0x0109`, object-table pointer
globals at `0x0963`/`0x0965`, inventory globals at `0x0969` through `0x096d`,
logic-cache globals at `0x096f` and `0x0979`, and the live logical-buffer
segment at `0x1365`. Object records are the observed 43-byte layout. The
combined logical buffer is 160 by 168 bytes; its low nibble is visual color and
its high nibble is priority/control.

The border detector is an independent screen oracle. It finds the observed red
rectangular border with a predominantly white interior and does not rely only
on interpreter memory.

## Limits

The controller is a research tool, not a replacement engine. Only SQ1.22's
2.917 adapter is implemented. State reads are coherent at semantic stops;
cached state while the VM is running is explicitly marked stale. Captures,
checkpoints, and prepared disks are disposable artifacts under `build/`.
Checkpoint restore reinstalls the semantic breakpoint reason saved with the
controller state before it accepts another mutation. This prevents a later
modal or string interaction from leaving the restored VM paired with the wrong
blocking hook.

QEMU's observed real-mode debugger path still permits one reliable execution
breakpoint. Stack-classified hook switching handles the known cycle, modal, and
shared-string modes, but unknown blocking loops still require new profile
evidence. Deferred key releases preserve every cycle boundary and remain
visible until QMP accepts them; the controller does not remove breakpoints or
run through unrecorded cycles merely to manufacture an input window.
