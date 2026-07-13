# Interpreter Controller

`tools/interpreter_controller.py` is a persistent, localhost-only controller
for cycle-stepped runs of a private original interpreter under QEMU. It wraps
QEMU's QMP lifecycle/input/screenshot interface and its GDB remote memory and
register interface behind JSON HTTP requests. The selected game is always
explicit, and preparation copies it to a disposable disk under `build/`.
Nothing under `games/` is modified.

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
to the next hook. `--capture-every-cycle` writes a PNG plus one JSONL metadata
record at every cycle stop.

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

Create a disposable raw clone and qcow2 play disk:

```bash
python3 -B tools/interpreter_controller.py prepare \
  --base-image build/freedos/freedos.img \
  --game-dir games/SQ1.22 \
  --dos-game-dir SQ122 \
  --raw-output build/interpreter-controller/session/sq122.raw \
  --output build/interpreter-controller/session/sq122.qcow2
```

Launch the persistent controller and visible Cocoa QEMU window:

```bash
python3 -B tools/interpreter_controller.py serve \
  --disk build/interpreter-controller/session/sq122.qcow2 \
  --game-dir games/SQ1.22 \
  --display cocoa,zoom-to-fit=on \
  --runtime-dir build/interpreter-controller/runtime \
  --capture-dir build/interpreter-controller/captures \
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

## HTTP surface

All endpoints bind to `127.0.0.1` by default. Mutating requests use JSON POST
bodies; state and image requests use GET.

| Endpoint | Result |
|---|---|
| `GET /v1/state` | Cycle number, room, score, all variables and flags, object records, modal state, loaded-image base, and DS |
| `GET /v1/variables`, `/flags`, `/objects` | Individual state families |
| `GET /v1/inventory`, `/logics` | Inventory table and live logic-cache records |
| `GET /v1/picture/priority.ppm` | Current 160 by 168 priority/control channel from the interpreter's combined logical buffer |
| `GET /v1/picture/visual.ppm` | Current visual channel from the same buffer |
| `GET /v1/screenshot.ppm`, `/screenshot.png` | Current VGA output through QMP `screendump` |
| `GET /v1/dialog` | Red-border/white-interior modal boxes plus the interpreter window-active state when safely readable |
| `POST /v1/cycles/step` | Execute through the next cycle or blocking semantic stop |
| `POST /v1/cycles/run` | Execute a bounded number of cycles |
| `POST /v1/cycles/run-until` | Execute until a nested state predicate matches or a bound is reached |
| `POST /v1/input` | Key down, key up, cycle-relative tap/type, or bootstrap `host_type` |
| `POST /v1/string-prompt/submit` | Enter text through the shared string editor and restore cycle control |
| `POST /v1/dialog/dismiss` | Dismiss the classified modal and restore cycle control |
| `POST /v1/movement/run-until` | Select a direction and run until a state predicate matches |
| `POST /v1/checkpoints`, `/checkpoints/restore` | QEMU named checkpoint management on the qcow2 session disk |
| `GET /v1/debug` | Stopped registers, stack bytes, image-relative IP, and the active semantic hook |
| `POST /v1/vm/quit` | Quit QEMU and shut down the HTTP server |

Predicates address nested fields with dotted paths. For example, this request
runs until ego's X coordinate is between 98 and 130 while the room remains 2:

```json
{
  "predicate": {
    "all": [
      {"path": "room", "op": "eq", "value": 2},
      {"path": "objects.0.x", "op": "between", "value": [98, 130]}
    ]
  },
  "max_cycles": 500
}
```

Supported predicate operators are `eq`, `ne`, `lt`, `le`, `gt`, `ge`, `in`,
`contains`, `between`, `truthy`, and `falsy`, with recursive `all`, `any`, and
`not` forms.

## State mappings

The SQ1.22 profile uses the locally verified 2.917 data layout: variables at
DS `0x0009`, packed high-bit-first flags at `0x0109`, object-table pointer
globals at `0x0963`/`0x0965`, inventory globals at `0x0969` through `0x096d`,
logic-cache globals at `0x096f` and `0x0979`, and the live logical-buffer
segment at `0x1365`. Object records are decoded as the observed 43-byte 2.917
records. The combined logical buffer is 160 by 168 bytes; its low nibble is the
visual color and its high nibble is priority/control.

The border detector is intentionally an independent screen oracle. It finds
the observed red rectangular border with a predominantly white interior and
does not depend solely on interpreter memory. A live `look` dialog produced
one box and agreed with the interpreter's window-active word; after dismissal
both checks became false.

## Limits

The controller is a version-specific research tool, not a generic replacement
engine. New interpreter builds require a separately evidenced profile and hash.
State reads are coherent at semantic stops; callers should not treat cached
state returned while the VM is running as a fresh snapshot. Checkpoints and
captures are generated artifacts under `build/` and are disposable.
