# Manhunter: San Francisco Playthrough Analysis

This chapter records a game-specific, clean-room reconstruction of the local
`MH2` evidence set. It is intended to become a repeatable game-level
conformance scenario and is not part of the portable AGI engine specification.
The analysis uses only local game resources, decoded logic and messages, and
locally rendered graphics.

This reconstruction is **partial**. The game identifies itself as *Manhunter:
San Francisco*, version 3.02, dated July 26, 1989, and its interpreter reports
version 3.002.149. The local game copy lacks `MH2VOL.3`. Thirty-one present
logic entries and large parts of the late graphics and sound sets select that
volume, so the available evidence cannot establish the final winning state or
a complete path to it.

## Evidence Method

The reusable logic index was generated with:

```bash
AGI_GAME_DIR=games/MH2 \
  python3 -B tools/logic_playthrough_index.py \
  --output build/playthrough/mh2/index.json
```

MH2 uses a version 3 combined directory with prefix `MH2`. Its directory
census advertises 96 present logics, 248 present pictures, 181 present views,
and 195 present sounds. The available volumes provide:

| Resource type | Readable | Unreadable because volume 3 is absent |
| --- | ---: | ---: |
| Logic | 65 | 31 |
| Picture | 177 | 71 |
| View | 114 | 67 |
| Sound | 122 | 73 |

The 65 readable logics expose six parser conditions, 135 explicit room
switches, 32 inventory mutations, and no score events or maximum-score
assignment. A qualitative picture sweep decoded all 177 pictures available
from the present volumes.

The playthrough indexer was extended to treat a missing volume file as an
explicit unreadable-resource result, alongside an invalid record or out-of-
range offset. Each missing logic remains in the index with its advertised
volume and offset instead of aborting the entire analysis.

## Missing Logic Boundary

The unavailable logic numbers are:

```text
131 132 133 161 164 165 168 170 171 173 174 175 176
178 179 180 181 183 184 185 186 187 188 189 190 191
192 193 194 195 196
```

These are not proved-unused directory artifacts. Logic 0's normal room
dispatcher contains direct branches to many of them, including 131, 132, 133,
164, 165, 168, 171, 173, 174, 176, 178, 179, 183, 184, 191, and 194. Readable
logic 172 also switches to missing logic 175. The missing set therefore cuts
through reachable room flow and includes most of the highest-numbered late-
game logic.

Two inventory objects also begin in missing rooms: the Hatchet in room 165 and
the Orb-on-a-Stick in room 170. Their acquisition conditions and later uses
cannot be reconstructed from this copy.

## Completion Model

MH2 does not use a numeric adventure score. None of the readable logics changes
the conventional score variable or declares a maximum. Winning must therefore
be defined by reaching the game's final story state, not by maximizing points.

The present resources do **not** expose that final state. Readable logic 146
contains the words `The End`, but its surrounding controls start and stop an
in-world presentation called *The Glorius Union*. Logics 147 and 149 contain
more Orb propaganda shown through the same local presentation mechanism. These
are inspectable exhibits within the game, not evidence that the game itself has
ended.

Likewise, `YOU WON` and `Congratulations` messages in logics 102, 117, 119,
122, and 123 belong to arcade or movement challenges. They signal success in a
local minigame, not whole-game completion.

Because the late room logics are absent, this chapter does not name a terminal
logic or claim a complete winning route. The eventual compatibility scenario
must identify the real final transition from a complete MH2 copy and verify it
under the original interpreter.

## Readable Story Progression

### Opening pursuit

Logics 153 and 154 date the opening September 4, 2004. The player recounts
being forced to become a Manhunter for the Orbs in New York, pursuing a killer,
and following him west aboard an alien ship. The opening sequence leads into
San Francisco and logic 124, where the player can take an ID Card and the
Manhunter Assignment Device, or MAD.

### Orb assignments

A phase value starts at 1. Each entry into logic 126 increments it, producing
two readable assignments:

| Phase after entry | Assignment |
| ---: | --- |
| 2 | Investigate a boat burning at Pier 5 |
| 3 | Investigate a human on the sign at Ghirardelli Square |

MAD supplies information and tracking for Tad Timov, Peter Brown, Phillipe
Cook, Noah Goring, Mic Stone, and Zac West. Its readable target results include
the Bank of Canton in Chinatown, Ghirardelli Square, Pier 5, and the Alliance
computer room.

The travel interface exposes a San Francisco investigation network containing
the warehouse, temple, Hyde Street Pier, Bank of Canton, Embarcadero Fountain,
crash scene, Pier 5, Ferry Building, the Manhunter's apartment, Tad Timov's
apartment, Transamerica Pyramid, doctor's house, laundry, private club, shop,
cable-car barn, scientist's house, wax museum, and Ghirardelli Square.
Availability is state-dependent; the list is not a claim that every destination
can be selected immediately.

### Readable investigation chains

The available rooms establish several connected object and clue groups:

- Pier and waterfront rooms contain a Dragon Note, Newspaper, Mallet, broken
  Fang, Laundry Receipt, and paths involving Alcatraz and a ladder.
- Residential and institutional rooms provide a Driver's License, Empty Flask,
  Cloth, Camera, Muzzle, Statue, Matchbook, letters, Empty Gun, Orb Card, and
  Walking Stick.
- A Three Aces game in logic 123 offers the Flashlight, Lantern, Rat Mask, Key,
  and Medallion as prize choices. The local win does not itself end the game.
- Logic 136 converts the Empty Flask to a Full Flask and supplies Letter 2.
  Logic 142 uses the Fang as a cutting tool and supplies Letter 1.
- Logic 138 reveals Orb directives and genetic work on Rat/Dog/Human subjects.
  Its records say that test subjects failed in dry heat, that loyal subjects
  are to be released near Fisherman's Wharf, and that the researcher now wants
  to save mankind.
- Logic 150 reports that a person emerging from the sewer has the Viewer and
  that the Rats call Phil `King`, connecting the investigation back to the
  pursued killer.

The readable failure-message catalog also anticipates later robots, acid,
rats, bats, gas, lava, slaves, gates, and a place described as Hell. Most of
the room implementations for that material fall in missing volume 3, so these
messages are clues to omitted gameplay rather than enough evidence to specify
its solutions.

## Inventory Evidence

The inventory table contains 32 entries. The table below records the ordinary
initial room owner and, where readable, the logic that can acquire or transform
the item.

| Id | Item | Initial room | Readable acquisition or transformation |
| ---: | --- | ---: | --- |
| 0 | nothing | 199 | Placeholder |
| 1 | Dragon Note | 112 | Logic 112 |
| 2 | ID Card | 124 | Logic 124 |
| 3 | Newspaper | 112 | Logic 112 |
| 4 | Scroll | 122 | Logic 122 |
| 5 | Laundry Receipt | 111 | Logic 111; consumed in logic 134 |
| 6 | Muzzle | 127 | Logic 127; also consumed/reacquired in readable scenes |
| 7 | Fang | 111 | Logic 111 |
| 8 | Walking Stick | 134 | Logic 163 |
| 9 | Ring | 132 | Acquisition logic unavailable |
| 10 | Rat's Paw | 133 | Acquisition logic unavailable; readable consumption in logic 139 |
| 11 | Mallet | 109 | Logic 109 |
| 12 | Driver's License | 115 | Logic 115 |
| 13 | Empty Flask | 115 | Logic 115; converted in logic 136 |
| 14 | MAD | 117 | Taken in logic 124 |
| 15 | Cloth | 125 | Logic 125 |
| 16 | Statue | 128 | Logic 128 |
| 17 | Camera | 118 | Logic 118 |
| 18 | Full Flask | 136 | Logic 136 |
| 19 | Matchbook | 138 | Logic 138 |
| 20 | Letter 1 | 142 | Logic 142 |
| 21 | Empty Gun | 144 | Logic 144 |
| 22 | Rat Mask 1 | 123 | Three Aces prize logic |
| 23 | Hatchet | 165 | Acquisition logic unavailable |
| 24 | Letter 2 | 136 | Logic 136 |
| 25 | Orb-on-a-Stick | 170 | Acquisition logic unavailable |
| 26 | Orb Card | 147 | Logic 147 |
| 27 | Flashlight | 123 | Three Aces prize logic |
| 28 | Lantern | 123 | Three Aces prize logic |
| 29 | Rat Mask 2 | 123 | Three Aces prize logic |
| 30 | Key | 123 | Three Aces prize logic |
| 31 | Medallion | 123 | Three Aces prize logic |

The Three Aces logic exposes several prizes, but static availability does not
prove that all prize branches can be collected in one playthrough. That choice
structure must be traced before turning the inventory list into a required-
items route.

## Partial Candidate Route

The following is the strongest route skeleton supported by the readable
resources. It is not a command-by-command winning walkthrough.

1. Complete the local opening verification, follow the New York-to-San
   Francisco pursuit, and take the ID Card and MAD in logic 124.
2. Receive the Pier 5 burning-boat assignment. Use MAD records and tracking,
   unlock the waterfront travel destinations, inspect the pier and nearby
   rooms, and collect the readable notes, Mallet, Fang, Laundry Receipt,
   Driver's License, and flask as their interactions become available.
3. Return through the assignment flow and receive the Ghirardelli Square sign
   assignment. Continue opening the residential, commercial, museum, cable-car,
   and Ghirardelli destinations.
4. Complete the readable object chains: use the laundry receipt, use the Fang
   where cutting is required, transform the flask, collect both letters, and
   inspect the scientist's directives describing the hybrid subjects and
   Fisherman's Wharf release.
5. Win the required local arcade or movement challenges and select prizes only
   as demanded by subsequent object conditions. Collect the Matchbook, Empty
   Gun, Orb Card, Walking Stick, and other accessible late objects.
6. Follow the sewer/Viewer/Phil trail into the volume-3 room network. No exact
   sequence after this boundary can be derived from the current files.

The first five steps identify actionable investigation groups, not a proved
single ordering. Missing rooms 131-133 already interrupt relatively early
travel and object state, while rooms 164 onward remove substantial late-game
logic. A complete copy is required to resolve alternate prize choices,
dependencies, and the terminal state.

## Failure and Retry Evidence

Like MH1, MH2 often treats death as a narrated local retry. Readable logics use
phrases such as "back up to a few minutes before your fatal mistake" and offer
reincarnation or restart controls within arcade sequences. The failure catalog
includes falling, incorrect controls, robots, acid, rats, bats, exhausted
camera flashes, gas, lava, and releasing hazards into occupied areas.

The exact rewind state is not yet mapped. A future replay must distinguish:

- local arcade failure followed by immediate restart;
- narrated death followed by restoration to an earlier room state;
- ordinary puzzle blockage with no state loss;
- the true whole-game terminal sequence.

## What Is and Is Not Established

The current evidence establishes:

- the game identity and interpreter version;
- the absence of numeric scoring in all readable logic;
- the opening pursuit, acquisition of MAD and the ID Card, and two Orb
  assignments;
- the readable San Francisco travel network and MAD records;
- the 32-entry inventory model and 32 readable inventory mutations;
- the hybrid-subject and Fisherman's Wharf plot disclosures;
- several local arcade success and death/retry contracts.

It does not establish:

- the actual whole-game terminal logic or final observable state;
- a complete reachable path through either assignment and the later plot;
- acquisition and use of objects owned by missing rooms;
- the exact Three Aces prize combination required for completion;
- late Hell/lava/slave puzzle semantics, movement, timing, or retry state;
- complete picture, view, and sound coverage.

## Work Required for a Replay

1. Obtain `MH2VOL.3` from the same MH2 release and confirm its directory and
   resource headers match the existing files.
2. Regenerate the logic index, resource-reference audit, and all graphics and
   sound censuses. The expected first check is that all 31 missing logics and
   their associated media become readable.
3. Trace the complete assignment and room graph, inventory prerequisites,
   Three Aces prize choices, late hazard solutions, and true final transition.
4. Verify each death/retry class and exact restored state under interpreter
   3.002.149.
5. Record a full original-interpreter playthrough with assignment, inventory,
   room, branch-choice, and terminal checkpoints, then package it as a
   deterministic game-level compatibility scenario.
