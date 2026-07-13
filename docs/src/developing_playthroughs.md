# Developing and Validating Playthroughs

This chapter describes a clean-room workflow for turning local game resources
into a precise, repeatable playthrough. It combines static analysis with
controlled experiments in the original interpreter. The aim is not merely to
write a walkthrough that sounds plausible. The finished route should state
the required game state, the exact player action, the expected state change,
and the conditions under which the step must be retried or rejected.

The static workflow applies to every selected game. The current interpreter
controller is narrower: its only implemented adapter is for the local
SQ1.22/2.917 interpreter. Do not point it at another interpreter merely because
the resource format looks similar. A new build needs a separately evidenced
profile and adapter as described in
[Interpreter Controller](./interpreter_controller.md).

## What a finished playthrough must prove

A useful playthrough has three related outputs:

1. A prose route that a person can follow.
2. A machine-readable state graph that records preconditions, actions,
   automatic transitions, waits, random retries, and failure edges.
3. Dynamic confirmation from the original interpreter, including state
   snapshots and enough trace data to distinguish a correct hypothesis from a
   lucky visual result.

Treat every important transition as a state contract:

| Part | Question |
|---|---|
| Starting state | Which room, variables, flags, inventory, object states, coordinates, and input mode must already hold? |
| Action | Which command, key, movement segment, wait, or dialog response occurs? |
| Postcondition | What observable state proves that the action succeeded? |
| Invariants | What must remain true while the action is in progress? |
| Abort conditions | Which death, wrong-room, modal, timer, or object state means the hypothesis failed? |
| Bound | How many interpreter cycles may be spent before stopping to investigate? |
| Evidence | Which logic offsets, messages, object metadata, and picture/control resources support the contract? |

A screenshot alone is not a sufficient postcondition. A screen can look right
while the required flag, inventory item, score award, or room controller is
wrong. Conversely, a correct input can open a modal or shared string editor
before its eventual state change. Record both the semantic stop and the game
state.

## Work from static evidence first

Interactive play should test a hypothesis derived from local evidence. It
should not be the primary way to discover what to try.

### Select and inventory the evidence set

Always select the private input explicitly. For example:

```bash
export AGI_GAME_DIR=games/SQ1.22
python3 -B tools/logic_playthrough_index.py \
  --output build/playthrough/sq1_22/index.json
python3 -B tools/disassemble_logic.py 1 2 3 --messages
```

The playthrough index is a first-pass inventory of conditions, actions,
parser-word groups, messages, and score-like operations. It is not a reachability
proof. Inspect the full disassembly around every candidate event. A syntactic
score increment may be:

- guarded by a one-shot flag;
- part of a mutually exclusive route;
- canceled by a later subtraction;
- reachable only after another room controller changes state;
- a death, joke, or rollback branch rather than part of a winning route.

Record the selected game directory, interpreter version, resource counts, and
maximum-score source in the playthrough chapter and graph provenance.

### Expand every scoring action into preconditions

For each selected award, trace backward until all required conditions are
explicit. Common preconditions include:

- current and previous room variables;
- flags and phase variables set by other logics;
- carried, absent, consumed, or room-local inventory items;
- parser word groups and acceptable synonym combinations;
- ego baseline or full-width containment in a rectangle;
- another object's position, distance, animation frame, motion mode, or
  visibility;
- an active or inactive modal/string input mode;
- timer variables, cycle counts, or completion flags;
- random results and the state needed to retry safely.

Do not reduce this to “go there and type the command.” Parser acceptance is a
conjunction of words, state, location, and timing. The same words can be
ignored, rejected, or interpreted differently in another phase.

### Reconstruct room topology from pictures and logic

Render both channels for every room on the proposed route:

```bash
export AGI_GAME_DIR=games/SQ1.22
python3 -B tools/render_picture.py 3 --channel visual \
  --output build/playthrough/sq1_22/picture_003_visual.ppm
python3 -B tools/render_picture.py 3 --channel control \
  --output build/playthrough/sq1_22/picture_003_control.ppm
```

The visual picture explains what the scene represents. The priority/control
picture explains where movement is likely to be accepted. The latter is often
the more important navigation source.

Use these rules when planning movement:

- Ego occupies a baseline footprint, not a single point. Test the entire
  width from its left X coordinate at its baseline Y coordinate.
- Control values 0 and 1 are blocked by default in the current controller,
  but room logic can change horizons, fixed priority, block handling, object
  collision, or the effective geometry.
- A base picture is not necessarily the current picture. Overlays and
  geometry-changing actions can alter the live priority channel, so capture it
  again after the relevant state transition.
- A visually open region can be blocked, while an unremarkable colored notch
  can be the intended door or ramp.
- A wall on the current screen often means the route passes through another
  room. Multi-level rooms commonly use an elevator, stair, corridor, or
  adjacent-room loop rather than a direct crossing.
- Room exits are state transitions. Trace the room logic that recognizes the
  boundary instead of assuming that every screen edge leads somewhere.

If a direct route fails, do not repeatedly steer at the obstacle. Re-open the
room logic and the visual/control pair, identify the actual topology, and form
a new route hypothesis.

### Separate deterministic waits from randomness

Static resources often reveal the condition that ends a wait even when they
cannot predict when it will occur. Represent deterministic timing as a bounded
state wait, such as a phase variable reaching a value or an animation
completion flag becoming set. Do not replace it with an arbitrary wall-clock
sleep after interpreter discovery.

Represent randomness explicitly. A random dialogue choice, gambling result,
or wandering-object phase should have:

- a success predicate;
- a failure or continue predicate;
- a checkpoint from which retry is valid;
- a resource or inventory bound that prevents endless destructive retries.

Random failure is not evidence that the route hypothesis is wrong. Failure to
reach either the documented success or retry state within the cycle bound is.

## Build an explicit state graph

The reusable graph should distinguish states from actions. In the existing
SQ1.22 graph, each award has a `precondition` node followed by a
`score_action` node. Edges contain player input, movement, waiting, automatic
transitions, and random retry behavior.

A minimal fragment has this shape:

```json
{
  "game": {"maximum_score": 2},
  "score_route": ["score_example"],
  "nodes": [
    {
      "id": "ready_example",
      "kind": "precondition",
      "room": "6",
      "requirements": ["v52=0", "ego width inside target rectangle"]
    },
    {
      "id": "score_example",
      "kind": "score_action",
      "score_delta": 2,
      "evidence": [{"logic": 6, "ip": "00e0"}]
    }
  ],
  "edges": [
    {
      "from": "ready_example",
      "to": "score_example",
      "kind": "player_action",
      "instruction": "submit the statically accepted command and wait for its completion flag"
    }
  ]
}
```

Keep requirements machine-readable where practical, but retain evidence
locations and prose for distinctions such as full-width versus left-baseline
geometry. Validate that every selected score node occurs exactly once in the
route and that the score ledger equals the declared maximum.

Render the graph with:

```bash
python3 -B tools/render_playthrough_graph.py \
  docs/src/games/sq1_22_success_path.json \
  --output docs/src/games/sq1_22_success_path.svg
```

The renderer validates node references and the score ledger before generating
the vertical Graphviz diagram. A valid graph proves internal consistency, not
dynamic reachability. Dynamic replay remains a separate evidence layer.

## Plan each dynamic experiment before running it

Before sending input, write down:

- the state snapshot from which the experiment starts;
- the static logic and picture evidence;
- the smallest action that tests the hypothesis;
- the expected postcondition and state delta;
- invariants and abort predicates;
- the maximum cycle count;
- the checkpoint to restore if the hypothesis fails.

Prefer one semantic question per experiment. “Can ego reach this side of the
control opening without leaving room 3?” is useful. “Navigate the whole ship
until something interesting happens” is not. Small experiments make state
deltas and failed assumptions understandable.

## Start an interpreter-controller session

The commands below are specifically for the implemented SQ1.22/2.917 adapter.
First create a disposable play disk; never modify `games/`:

```bash
python3 -B tools/interpreter_controller.py prepare \
  --base-image build/freedos/freedos.img \
  --game-dir games/SQ1.22 \
  --dos-game-dir SQ122 \
  --raw-output build/interpreter-controller/session/sq122.raw \
  --output build/interpreter-controller/session/sq122.qcow2
```

In a persistent terminal, launch visible QEMU and the localhost API:

```bash
python3 -B tools/interpreter_controller.py serve \
  --disk build/interpreter-controller/session/sq122.qcow2 \
  --game-dir games/SQ1.22 \
  --display cocoa,zoom-to-fit=on \
  --runtime-dir build/interpreter-controller/runtime \
  --capture-dir build/interpreter-controller/captures \
  --port 8765
```

Add `--capture-every-cycle --capture-logical-buffers` when producing a complete
recording. Those options deliberately trade throughput and disk space for an
image/state record at every cycle.

QEMU starts paused at reset. Resume it, allow DOS to boot, launch the copied
game, and discover the first interpreter hook:

```bash
curl -sS -X POST http://127.0.0.1:8765/v1/vm/continue \
  -H 'Content-Type: application/json' -d '{}'
sleep 5
curl -sS -X POST http://127.0.0.1:8765/v1/input \
  -H 'Content-Type: application/json' \
  -d '{"action":"host_type","text":"cd \\sq122\nsierra\n"}'
sleep 2
curl -sS -X POST http://127.0.0.1:8765/v1/instrument/discover \
  -H 'Content-Type: application/json' \
  -d '{"wait_for_hook":true}'
```

The two sleeps are bootstrap waits for firmware, DOS, and program loading.
After discovery, use interpreter cycles and state predicates instead of host
time.

Confirm the selected adapter and initial state:

```bash
curl -sS http://127.0.0.1:8765/v1/profile | python3 -m json.tool
curl -sS http://127.0.0.1:8765/v1/state | python3 -m json.tool
```

## Inspect state before acting

Useful read-only endpoints are:

```text
GET /v1/state
GET /v1/variables
GET /v1/flags
GET /v1/objects
GET /v1/inventory
GET /v1/logics
GET /v1/dialog
GET /v1/input/state
GET /v1/trace?since=0&limit=1000
GET /v1/picture/visual.ppm
GET /v1/picture/priority.ppm
GET /v1/screenshot.png
```

Save live images without advancing the interpreter:

```bash
curl -sS http://127.0.0.1:8765/v1/picture/priority.ppm \
  -o build/interpreter-controller/live_priority.ppm
curl -sS http://127.0.0.1:8765/v1/screenshot.png \
  -o build/interpreter-controller/live_screen.png
```

Compare the live room, ego position and width, current logic/resume IP,
inventory, relevant variables and flags, input mode, and pending keys with the
planned starting contract. If the precondition is false, do not send the
action merely to see what happens.

## Prefer semantic transactions to raw keys

`POST /v1/transactions` combines a precondition, one semantic action,
postconditions, invariants, and a cycle bound. It also returns a state delta
and the relevant trace slice. For example, a deterministic wait can be stated
as:

```bash
curl -sS -X POST http://127.0.0.1:8765/v1/transactions \
  -H 'Content-Type: application/json' \
  -d '{
    "idempotency_key":"wait-room1-phase-33",
    "precondition":{"path":"room","op":"eq","value":1},
    "action":{
      "type":"wait_for_state",
      "predicate":{"path":"variables.33","op":"eq","value":1},
      "max_cycles":2000,
      "invariants":[{
        "name":"remain-in-room-1",
        "predicate":{"path":"room","op":"eq","value":1}
      }]
    },
    "postcondition":{"path":"variables.33","op":"eq","value":1},
    "max_cycles":2000
  }' | python3 -m json.tool
```

For a parser action, use `{"type":"command","text":"..."}`. For a
shared string editor, use `submit_string`; for a direction or movement
contract, use `select_direction`, `move_until`, `waypoints`, or
`navigate_priority`. The full action list is in the controller chapter.

Interpret transaction results carefully:

- `succeeded` means an expected postcondition was observed.
- `already_satisfied` means no input was needed.
- `precondition_failed` means the plan did not apply to the current state.
- `invariant_failed`, `interrupted`, or `timeout` means stop and investigate.
- `outcome_certainty` distinguishes an observed result from delivered input
  whose game outcome has not yet been proved.

An idempotency key prevents accidental duplicate input within the current
timeline. Reusing the same key and request returns the recorded result. A
different request with the same key is rejected. Restoring a checkpoint clears
the cache because the game state has moved backward.

### Treat input delivery and game outcome separately

QEMU may accept key-down just before the interpreter reaches its next hook and
then reject key-up because the VM is already stopped. The controller records
that as `release_pending`, retains the held-key state, and attempts bounded
reconciliation before another tap. It is not proof that the game action
failed.

Check `/v1/input/state` when input behaves unexpectedly. Use these recovery
operations instead of blindly repeating a key:

```bash
curl -sS -X POST http://127.0.0.1:8765/v1/input \
  -H 'Content-Type: application/json' \
  -d '{"action":"reconcile","max_attempts":4}'

curl -sS -X POST http://127.0.0.1:8765/v1/input \
  -H 'Content-Type: application/json' \
  -d '{"action":"release_all","max_attempts":8}'
```

Success must come from the postcondition, not from the fact that QMP accepted a
keystroke.

## Handle input modes and dialogs explicitly

The shared text editor is an interpreter input mode, not a special title-screen
case. The same mode can be used for a name, a machine, a code, or another
game-defined prompt. Use the current `stop_reason` to choose the operation:

- `cycle_boundary`: ordinary commands and movement are available;
- `string_prompt_wait`: submit through `/v1/string-prompt/submit` or a
  `submit_string` transaction action;
- `modal_wait`: identify and dismiss the current dialog.

Do not press Enter merely because text is visible. First query the dialog:

```bash
curl -sS http://127.0.0.1:8765/v1/dialog | python3 -m json.tool
```

Pass the returned stable `dialog_id` when dismissing it:

```bash
curl -sS -X POST http://127.0.0.1:8765/v1/dialog/dismiss \
  -H 'Content-Type: application/json' \
  -d '{"key":"ret","dialog_id":"DIALOG_ID_FROM_GET"}'
```

The operation is idempotent. An absent dialog returns `already_absent`; a
different dialog returns `dialog_mismatch` without input. This prevents a late
Enter from leaking into ordinary gameplay after a dialog has already closed.

## Plan and execute movement conservatively

The live priority planner can test a local-room navigation hypothesis without
moving ego. The example coordinates assume the statically documented room-3
keycard area; replace them with the supported goal for the current room:

```bash
curl -sS -X POST http://127.0.0.1:8765/v1/movement/plan \
  -H 'Content-Type: application/json' \
  -d '{"x":120,"y":70,"goal_tolerance":1}' \
  | python3 -m json.tool
```

It checks the full ego baseline footprint and returns both the pixel path and
compressed turn waypoints. A blocked goal is useful evidence; it is not an
invitation to force movement through it.

Execute an accepted local plan only when static room logic agrees:

```bash
curl -sS -X POST http://127.0.0.1:8765/v1/movement/navigate \
  -H 'Content-Type: application/json' \
  -d '{
    "x":120,
    "y":70,
    "goal_tolerance":1,
    "max_cycles_per_segment":500,
    "invariants":[{
      "name":"remain-in-room",
      "predicate":{"path":"room","op":"eq","value":3}
    }]
  }' | python3 -m json.tool
```

Use explicit waypoints when the desired route is known:

```bash
curl -sS -X POST http://127.0.0.1:8765/v1/movement/waypoints \
  -H 'Content-Type: application/json' \
  -d '{
    "waypoints":[
      {"x":98,"axis_order":"x_then_y"},
      {"x":98,"y":60,"axis_order":"y_then_x"}
    ],
    "max_cycles_per_segment":500,
    "preserve_room":true
  }' | python3 -m json.tool
```

Waypoint completion uses direction-aware crossing rather than exact coordinate
equality, so a step size greater than one cannot skip the target forever.

The planner is intentionally not a whole-game solver. It does not infer:

- another room needed to get around a wall;
- elevators, stairs, doors, or multi-level topology;
- dynamic collision with moving objects;
- a horizon or control override installed by room logic;
- a deliberate room transition.

Represent those as explicit stages with their own preconditions and
postconditions. A local plan should normally preserve the current room. A room
exit should instead be a separate contract whose postcondition is the expected
new room and entry boundary.

## Use guarded cycle waits

For animation, timers, wandering objects, or random phases, run until a state
predicate while protecting assumptions:

```bash
curl -sS -X POST http://127.0.0.1:8765/v1/cycles/run-until-guarded \
  -H 'Content-Type: application/json' \
  -d '{
    "predicate":{"path":"flags.35","op":"truthy"},
    "invariants":[{
      "name":"stay-in-room",
      "predicate":{"path":"room","op":"eq","value":1}
    }],
    "max_cycles":2000
  }' | python3 -m json.tool
```

Choose the bound from static timing evidence where possible, with enough
margin for the observed interpreter cadence. A timeout means the hypothesis or
bound needs review; it should not automatically trigger a larger blind wait.
Add positive abort predicates only when static logic identifies a distinct
failure state; do not invent a generic death or failure flag.

## Checkpoint risky and random transitions

Create a checkpoint only at a coherent stopped state:

```bash
curl -sS -X POST http://127.0.0.1:8765/v1/checkpoints \
  -H 'Content-Type: application/json' \
  -d '{"name":"before_random_retry"}'
```

Restore it with:

```bash
curl -sS -X POST http://127.0.0.1:8765/v1/checkpoints/restore \
  -H 'Content-Type: application/json' \
  -d '{"name":"before_random_retry"}'
```

The controller restores its held/pending key model with an in-session
checkpoint and clears cached transaction results. After restoring, re-read the
full state before retrying. Do not assume that a host-side plan cursor or an
old HTTP response still describes the VM.

Useful checkpoint locations are phase boundaries, before destructive random
events, and before a new uncertain route segment. Excessive checkpoints can
hide a mistaken state model; they are recovery points, not substitutes for
preconditions.

## Diagnose failure instead of improvising

When an experiment deviates from the plan, stop sending input. Inspect the
state, transition trace, current logic, screenshot, and live priority channel:

```bash
curl -sS 'http://127.0.0.1:8765/v1/trace?since=0&limit=20000' \
  | python3 -m json.tool
curl -sS http://127.0.0.1:8765/v1/logics | python3 -m json.tool
curl -sS http://127.0.0.1:8765/v1/debug | python3 -m json.tool
```

Then return to the static resource that owns the expected transition. Revise
the hypothesis before the next attempt.

| Symptom | Inspect first | Typical correction |
|---|---|---|
| Command has no effect | Room logic, parser word groups, phase flags, ego rectangle, input mode | Fix the missing precondition; do not try synonyms at random |
| Ego repeatedly hits a wall | Live priority screen, full baseline footprint, room exits and adjacent-room logic | Use the actual control opening or an alternate-room/elevator route |
| Movement never reaches an exact point | Ego step size, target direction, crossing predicate, dynamic collision | Use guarded crossing/tolerance and inspect the obstructing object |
| Expected room change does not occur | Boundary condition, Y/X gate, entry edge, horizon, prior room variable | Target the exact exit predicate instead of the visible screen edge |
| Execution stops returning to cycles | `stop_reason`, dialog oracle, current stack classification | Handle the modal or shared string editor semantically |
| A key appears stuck or repeats | `/v1/input/state` and input trace | Reconcile pending releases; do not repeat the action blindly |
| Score is wrong | Score delta, one-shot flags, alternative awards, subtraction branches | Re-audit reachability and exclusivity around every score operation |
| Random event keeps failing | Random controller state, inventory/money bound, checkpoint state | Verify the retry loop and restore point rather than changing unrelated actions |

The most productive question is usually “Which assumption in the starting
contract was false?” rather than “Which key should I try next?”

## Record replay evidence

Capture a semantic stop on demand with:

```bash
curl -sS -X POST http://127.0.0.1:8765/v1/captures/cycle \
  -H 'Content-Type: application/json' -d '{}'
```

Each immutable bundle under `CAPTURE_DIR/cycles/` contains a screenshot,
`cycle.json`, and optional visual/priority images. The metadata contains the
full state, delta from the previous recorded stop, and trace/input events.
`cycles.jsonl` is appended only after a bundle is complete and includes the
screenshot hash.

For each confirmed graph edge, preserve at least:

- starting and final room, score, coordinates, and entry boundary;
- relevant variable, flag, inventory, and object changes;
- the transaction result and predicate evaluations;
- modal or string-input transitions;
- cycle count for waits and movement;
- checkpoint/retry identity for random edges;
- the current logic context when the outcome differs from the hypothesis.

Do not silently rewrite the static theory to match one surprising run. Record
the failed hypothesis, identify the static reason it was wrong, update the
state graph, and replay from a known checkpoint. Corrections are part of the
clean-room evidence trail.

## End the session cleanly

Quit QEMU through the controller:

```bash
curl -sS -X POST http://127.0.0.1:8765/v1/vm/quit \
  -H 'Content-Type: application/json' -d '{}'
```

Confirm that neither the controller nor QEMU remains running before rebuilding
or replacing the session disk.

## General lessons

The main lessons from developing and exercising the controller are:

1. Static resources should choose the experiment; interactive play should
   confirm or refute it.
2. Consult the active room and controller logics regularly. Guessing becomes
   especially expensive when a missing phase flag or alternate-room route is
   mistaken for an input problem.
3. Navigation is a topology problem. The priority screen, ego footprint, room
   exits, and logic-installed overrides matter more than a visual straight
   line.
4. Treat player actions as state transactions, not keystrokes. Delivered input
   and successful game outcome are different facts.
5. Use state predicates for timing and explicit retry graphs for randomness.
   Wall-clock delays and unbounded waiting conceal errors.
6. Distinguish interpreter input modes from their game-specific purpose. A
   shared editor or modal loop can appear in many contexts.
7. Make failures safe and informative with invariants, abort predicates, cycle
   bounds, checkpoints, trace slices, and immutable recordings.
8. Keep automation local and conservative. A room-level priority planner is
   useful; an unverified whole-game planner merely guesses faster.
9. Break long routes into independently proved transitions. Small state deltas
   are easier to explain, reproduce, and encode in the graph.
10. Preserve corrections. A failed hypothesis that narrows the model is useful
    evidence, while undocumented trial and error is not.

## Completion checklist

Before calling a playthrough complete, verify that:

- every selected scoring action has static evidence and explicit preconditions;
- mutually exclusive, point-loss, death, and dead-end branches are identified;
- the score ledger reaches the declared maximum without double counting;
- every movement segment is supported by visual/control resources and room
  transition logic;
- waits have state predicates and finite bounds;
- random events have safe, bounded retry loops;
- parser commands include their location, state, and input-mode conditions;
- each dynamic action has a postcondition and relevant invariants;
- phase checkpoints restore to states that have been re-read and verified;
- dynamic traces and recordings agree with the machine-readable graph;
- remaining uncertainty is marked as such rather than presented as a proven
  instruction.
