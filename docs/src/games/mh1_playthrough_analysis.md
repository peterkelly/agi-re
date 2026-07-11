# Manhunter: New York Playthrough Analysis

This chapter records a game-specific, clean-room reconstruction of the local
`MH1` evidence set. It is intended to become a repeatable game-level
conformance scenario and is not part of the portable AGI engine specification.
The analysis uses only the local game resources, their decoded logic and
messages, and locally rendered graphics.

This reconstruction is **partial**. The selected game identifies itself as
*Manhunter: New York*, version 1.22, dated August 31, 1988, and its QA record
identifies interpreter 3.002.107. The local copy is incomplete: one present
logic entry and multiple graphics entries point outside the available volume
files. The readable resources establish the story phases, important state,
inventory flow, and terminal sequence, but they cannot yet prove one complete
playable path from start to finish.

## Evidence Method

The reusable logic index was generated with:

```bash
AGI_GAME_DIR=games/MH1 \
  python3 -B tools/logic_playthrough_index.py \
  --output build/playthrough/mh1/index.json
```

MH1 uses a version 3 combined directory with prefix `MH`. The directory census
found 165 logic entries, 256 picture entries, 145 view entries, and 139 sound
entries. Of those, 66 logics, 237 pictures, 138 views, and 101 sounds are marked
present. Sixty-five logics decode successfully and expose 11 parser conditions,
138 explicit room switches, and 93 inventory mutations.

Logic 136 does not decode because its directory entry selects volume 3 at
offset `0x1d323`, beyond the available `MHVOL.3` length of `0xfe00`. The
inventory table initially associates the Crowbar with room 136, so this is not
merely an unused directory artifact. Readable scripts also directly reference
unavailable views 7, 74, 75, 76, 77, and 85. A qualitative picture sweep
decoded 196 of the 237 present picture entries; the other 41 require absent or
truncated volume data.

The indexer was made tolerant of this condition: it now records the resource
number, volume, offset, and decode error in `unreadable_logics` and continues
with the readable evidence. That behavior is important for inspecting future
incomplete version sets without silently treating missing resources as empty
ones.

## Completion Model

MH1 does not use a conventional adventure-game score. No readable logic
assigns a maximum score, increments the normal score variable, or awards
points. Consequently, there is no numeric maximum to optimize. A winning
conformance scenario must instead reach the final narrative state through the
required story progression.

The central phase value begins at 1 and selects four Orb assignments:

| Phase | Assignment shown at headquarters |
| ---: | --- |
| 1 | Investigate the explosion at Bellevue Hospital |
| 2 | Find the missing maintenance robot from Grand Central Terminal |
| 3 | Investigate the dead Orb at Greenwood Cemetery |
| 4 | Investigate illegal access to the Alliance computer |

The phase-4 briefing also says that the Manhunter will be transferred to
Chicago after the assignment. This is a promise of the ending, not itself the
terminal state.

The strongest readable completion contract appears later. Logic 151 controls
a ship and accepts four bomb drops in four distinct target regions. It records
each successful region separately; only when all four have been completed does
it transfer to logic 162. Logic 162 runs the concluding cutscene and displays
`To be continued...`. Reaching that sequence after all four bomb states is the
winning terminal condition for this analysis.

## Runtime Story Model

### Headquarters, MAD, and travel

A new game initializes phase 1 and gives the player MAD. MAD provides records,
notes, and target tracking. The readable database includes Harvey Osborne,
Harold Jones, Phillipe Cook, Louis Redman, Reno Davis, and Anna Osborne. Its
tracking results identify Bellevue Hospital, Grand Central Terminal, Greenwood
Cemetery, and the Alliance computer room as phase-relevant targets.

The travel interface exposes New York destinations as they become useful,
including the player's home, 150 West 82nd Street, Vend-o-Deli, the Empire
State Building, Trinity Church, 21 Pearl Street, Prospect Park, Flatbush Bar,
Bellevue Hospital, the American Museum of Natural History, Strawberry Fields,
Grand Central Terminal, Wretched Excess, Coney Island, Drier Offerman Park,
Greenwood Cemetery, a Times Square theater, and Abdul's Pawn Shop. Travel
availability is state-dependent; listing a destination here does not prove it
is selectable in every phase.

### Reports and phase changes

The Data Card shows this clue:

> The End is Near. The Way is Clear. Destroy the Lady, Before They are Ready.
> Phil is Trouble. He's a Double. He's an Eye, That's no Lie!

The report interface asks for one suspect name in phase 1 and three names in
phase 3. The readable control flow captures and parses those entries, presents
the report sequence, and changes phase 1 to phase 2. No explicit name-match
predicate is visible in logic 131, so the exact semantic significance of each
entered name remains to be verified in the original interpreter rather than
guessed from the prose.

Later assignments use a common completion flag. Returning home while that
flag is set changes phase 2 to phase 3, or phase 3 to phase 4, and returns the
player to the report/headquarters sequence. Bellevue logic 135 and the
Alliance computer logic 149 can set this flag, but the complete conditions and
ordering across every location have not yet been reduced to a route proof.

### Four modules and the Alliance system

Readable logic places four separately named modules in the world:

| Item | Acquisition logic | Observed role |
| --- | ---: | --- |
| Module A | 111 | One of four modules accepted by the late control system |
| Module B | 135 | Found in the Bellevue/maintenance-robot sequence |
| Module C | 113 | One of four modules accepted by the late control system |
| Module D | 150 | One of four modules accepted by the late control system |

Logic 154 accepts the four modules in separate interactions and records four
persistent installed states. Logic 149 presents the Alliance computer's
repair, supply, defense, patrol, security, and operation interfaces. Its
messages report four loaded bombs and include ship, transmitter, maintenance,
and harvest controls. It also sets the common assignment-completion flag and
can transfer into the final sequence of rooms.

### Ship sabotage

Logic 152 offers entry to the ship and a keypad-driven movement interface.
Logic 151 then tracks four independently completed bomb sites. Three target
regions accept a bomb while the ship is in one movement mode and the fourth
uses another. Re-entering an already completed region does not create a fifth
required state. When all four states are set, the game leaves the flight scene
for logic 162's ending.

This gives a precise late-game compatibility assertion even before the entire
route is known: one, two, or three distinct valid drops must not finish the
game; the transition occurs only after all four have been recorded.

## Inventory Evidence

The inventory table contains 28 entries. Thirteen numbered keycards and the
medallion begin in room 128, while several later objects have ordinary room
owners. Two entries are unnamed.

| Id | Name | Initial room or readable acquisition |
| ---: | --- | --- |
| 0-12 | One through Thirteen Keycards | Room 128 |
| 13 | Medallion | Room 128 |
| 14 | MAD | Given during initialization in logic 90 |
| 15 | Data Card | Room 129 |
| 16 | Module B | Logic 135 |
| 17 | Unnamed | Not resolved |
| 18 | Crowbar | Room 136, whose logic is unavailable |
| 19 | Stuffed Orb | Room 129 |
| 20 | Key | Logic 106 |
| 21 | Unnamed | Not resolved |
| 22 | Module A | Logic 111 |
| 23 | Module C | Logic 113 |
| 24 | Module D | Logic 150 |
| 25 | Badges | Room 145 |
| 26 | Stuffed Orbs | Room 129 |
| 27 | Badge | Room 145 |

Logic 128 contains the large keycard/medallion interaction sequence. Logic 129
contains Data Card and stuffed-Orb state, while logic 145 contains badge state.
Because logic 136 is unavailable and the Crowbar starts there, the current
input cannot establish whether the Crowbar is required for the winning route
or exactly how it is obtained.

## Partial Candidate Route

The following is a phase skeleton supported by readable state transitions. It
is deliberately not presented as a complete command-by-command walkthrough.

1. Complete the local game's opening verification, start a new game, receive
   MAD, and view the phase-1 Bellevue assignment at headquarters.
2. Use MAD records and tracking, investigate the available city locations, and
   collect phase-relevant objects. Read the Data Card and submit the phase-1
   report; its completion sequence changes the phase from 1 to 2.
3. Follow the Grand Central maintenance-robot assignment. The readable route
   network connects this broader investigation with Bellevue, the museum,
   Trinity Church, and other city scenes. Acquire Module A, Module B, the key,
   and any other accessible persistent items. Complete the assignment state
   and return home to advance from phase 2 to phase 3.
4. Investigate the Greenwood Cemetery assignment. The later readable network
   includes Coney Island, Drier Offerman Park, the theater, Abdul's Pawn Shop,
   and the cemetery. Collect the remaining accessible clues, keycards,
   medallion, badges, and modules. Submit the three-name report when requested,
   complete the assignment state, and return home to advance to phase 4.
5. Investigate the Alliance computer. Acquire Modules C and D if not already
   held, install all four modules through logic 154, and operate the Alliance
   system in logic 149 until it exposes the final ship path with four bombs.
6. Enter the ship, navigate to four distinct valid drop regions, and drop one
   bomb in each. The fourth recorded region transfers to logic 162 and the
   `To be continued...` conclusion.

The phase ordering and final four-bomb condition are strong evidence. Exact
movement, exact object dependencies, the proper order of city puzzles, report
answers, and Crowbar use remain provisional because the local input is
incomplete and no original-interpreter replay has yet closed the route.

## Failure and Recovery Evidence

MH1 frequently presents a fatal event and then rewinds to shortly before the
mistake rather than ending at DOS. Readable messages in the Bellevue, robot,
computer, ship, and late-location logic include variants of "fatal mistake"
and "back up to a few minutes before." This suggests that a conformance replay
must distinguish a local retry from a full restart or terminal loss.

The readable resources identify several broad failure classes:

- tampering with or failing to act around the maintenance robot;
- selecting an incorrect late control or ship button;
- colliding with guarded or hazardous regions;
- entering maze walls or using the wrong hall route;
- failing timed scene interactions;
- dropping bombs outside a valid target region.

The exact state restored by each retry has not yet been audited. Automated
replays should therefore checkpoint before dangerous scenes until the local
rewind behavior is mapped.

## What Is and Is Not Established

The current evidence establishes:

- the four assignments and their phase order;
- the absence of a numeric score or maximum-score objective;
- the MAD records, target locations, travel destinations, and Data Card clue;
- the four-module late-game requirement;
- the Alliance computer and four loaded bombs;
- four distinct bomb-completion states and the transition to logic 162 only
  when all four are set;
- the final `To be continued...` narrative sequence.

It does not yet establish:

- a fully reachable puzzle-by-puzzle path through every phase;
- whether logic 136 and the Crowbar are mandatory for completion;
- exact report text accepted or rejected by the running interpreter;
- exact controls, movement, timing, and retry-state restoration;
- complete picture/view coverage for the missing local volume data.

## Work Required for a Replay

1. Obtain a complete MH1 evidence copy containing the bytes addressed by logic
   136 and the currently unavailable picture and view records.
2. Regenerate the logic index, resource-reference audit, and picture/view
   sweeps, then compare their directory metadata with this incomplete copy.
3. Trace every condition that sets the common assignment-completion flag and
   reduce each phase to exact object, location, and interaction prerequisites.
4. Verify report inputs, travel unlocks, the Crowbar chain, module installation
   order, and retry restoration under the original 3.002.107 interpreter.
5. Record a complete original-interpreter playthrough with phase, inventory,
   module, bomb, and terminal-state checkpoints and package it as a deterministic
   game-level compatibility scenario.
