# Manhunter: New York Playthrough Analysis

This chapter is a fresh clean-room reconstruction of a winning route through
the replacement local `MH1` evidence set. It was derived from the current
game's logic, messages, vocabulary, object list, pictures, and views. It does
not reuse the earlier analysis of the incomplete copy, and no external
walkthrough or AGI documentation was consulted.

The result is a **static route specification**, not yet a replay script. The
assignment order, required portable objects, late-game computer and ship
chains, and terminal predicate are source-proven. Exact movement through every
arcade sequence and the complete original-interpreter input stream still need
dynamic reconstruction.

## Evidence Method

The reusable index for this analysis was generated with:

```bash
AGI_GAME_DIR=games/MH1 \
  python3 -B tools/logic_playthrough_index.py \
  --output build/playthrough/mh1-replacement/index.json
```

The selected game uses interpreter 3.002.102 and the v3 combined resource
layout. All 66 present logic resources decode. The game also contains 237
pictures, 138 views, and 99 valid script-addressable sounds. Every resource
reference made by readable logic resolves. Two malformed sound-directory tail
entries are not referenced by any script and are irrelevant to the route.

The inventory table contains 28 slots. The route analysis traced every
inventory mutation, every constant room switch, the travel map, the assignment
phase variable, all recognized report names, and every incoming edge to the
ending logic. Representative ending pictures were rendered locally to check
scene identity; they show the antagonist, ship explosions, and the final
aftermath, but the logic remains the authority for ordering.

No logic assigns or changes a conventional numerical score or maximum-score
value. For this game, “maximum score” therefore contributes no additional
criterion: winning means reaching the unique continuation ending without
entering a retry or death branch.

## Story and Terminal State

The player is a Manhunter in Orb-occupied New York. The Orb assignments begin
with an explosion at Bellevue Hospital, continue with a missing maintenance
robot at Grand Central Terminal and a dead Orb at Greenwood Cemetery, and end
with illegal access to the Alliance computer. The investigations expose a
resistance plot, Phil's double role, four ship modules, and the means to use an
Orb ship against four targets.

Logic 162 is the winning terminal sequence. It has no outgoing room transition
and eventually displays `To be continued...`. Its only ordinary incoming edge
is from the ship/bomb logic, logic 151. That edge is taken only when all of the
following are true:

- the bomb flight is in its completion phase;
- the late-story authorization flag is set;
- the flight state has reached stage 12; and
- all four distinct target-completion flags are set.

The four flags are set by separate bomb-drop regions. A single successful drop
cannot satisfy more than its own region, so the terminal predicate proves that
the winning flight requires all four targets.

## Global Route Constraints

1. Keep the MAD, the game's tracking and travel interface. Major assignments
   are reached through its map rather than a single continuous room graph.
2. Preserve the Data Card until the report sequence has consumed its clue.
   The card states: `Destroy the Lady, Before They are Ready` and identifies
   Phil as a double agent and an Eye.
3. Collect Module A, Module B, Module C, and Module D. The cockpit installation
   logic removes each module from inventory at a separate control position;
   all four positions are therefore genuine prerequisites.
4. Preserve the key, crowbar, badges, medallion, and accumulated keycards until
   their local access checks have been passed. The keycard inventory is encoded
   as mutually exclusive “One Keycard” through “Thirteen Keycards” entries,
   not thirteen independently carried cards.
5. Treat deaths as retry branches rather than forward progress. Many fatal
   scenes enter a shared rewind logic that explicitly returns to a few minutes
   before the mistake.
6. Complete all four bombing regions. Leaving the ship sequence after fewer
   than four successful regions cannot reach logic 162.

## Assignment and Report State

The assignment phase is a four-state progression. The observable assignment
messages are:

| Phase | Assignment |
| ---: | --- |
| 1 | Investigate the explosion at Bellevue Hospital |
| 2 | Investigate the missing maintenance robot at Grand Central Terminal |
| 3 | Investigate the dead Orb at Greenwood Cemetery |
| 4 | Investigate illegal access at the Alliance computer |

Completing the first report advances the phase from 1 to 2. Later handoffs
advance phases 2 to 3 and 3 to 4. The final assignment message promises a
transfer to Chicago after the investigation, but the actual route instead
continues into the Alliance computer and ship climax.

The report input uses the same full-name parser as the MAD occupant database.
Recognized names include Harvey Osborne, Anna Osborne, Harold Jones, Phillipe
Cook, Louis Redman, and Reno Davis, with spelling variants recorded in the
game vocabulary. Recognition alone is not proof that a name is a correct
answer for a particular report: recognized names set separate evidence flags,
and the surrounding assignment state decides their consequence. The complete
name order for an automated replay remains a dynamic validation item.

## Candidate Winning Route

### Opening investigation and Bellevue

1. Start the game, retain the MAD, and accept the Bellevue Hospital assignment.
2. Use the MAD's occupant records, notes, tracking display, and travel map to
   inspect the named people and assignment locations. The database recognizes
   the suspects listed above and can track available targets.
3. Follow the Bellevue investigation through its signal and room puzzles.
   Obtain the key in logic 106 when the close-up prompt makes it available.
4. Complete the first reporting cutscene. The report consumes typed names and
   returns the player home for new orders; successful progression changes the
   assignment phase to the missing-robot investigation.

### Grand Central and the maintenance robot

1. Travel to Grand Central Terminal and follow the maintenance-robot trail.
   The scripts warn that direct tampering makes the robot self-destruct.
2. Complete the associated movement and close-up sequences rather than waiting
   through the fatal branches.
3. Recover Module B from the robot-remains area in logic 135. The module is
   placed in inventory only after the appropriate action prompt and local
   state are both active.
4. Finish the report/assignment handoff that advances the story toward the
   Greenwood Cemetery case.

### Greenwood, Coney Island, and the city evidence chain

1. Investigate Greenwood Cemetery and the dead Orb. Continue following MAD
   tracking targets and the travel destinations opened by the current phase.
2. Obtain the Data Card and read its complete clue before reporting. The report
   sequence can request up to three full names in this phase.
3. At Coney Island, complete the carnival games needed by the prize logic.
   The scripts expose Balloons and Darts, Kewpie Doll Baseball, and Rings and
   Bottles, and make the Data Card, stuffed Orb items, and related prizes part
   of this chain.
4. In Central Park, use the MAD-derived route through the mined area. Wrong
   paths trigger the mine death; the valid path leads past named landmarks.
   Take the crowbar when its action becomes available.
5. Complete the keycard/medallion and badge-selection chains. The game replaces
   the current keycard-count item as the count changes and later offers badge
   and badges inventory states for access checks.

### Collect the four ship modules

The modules are acquired in four different room logics and installed at four
different cockpit controls:

| Module | Acquisition evidence | Required later behavior |
| --- | --- | --- |
| A | Logic 111, after the candle/match room sequence | Removed at its cockpit position |
| B | Logic 135, in the maintenance-robot chain | Removed at its cockpit position |
| C | Logic 113, after the button/close-up sequence | Removed at its cockpit position |
| D | Logic 150, after the handle and guard-robot sequence | Removed at its cockpit position |

The acquisition order can vary where the travel map permits it, but cockpit
completion cannot be faked by carrying only one or two modules. The installer
tests and consumes each named inventory entry independently.

### Alliance computer

1. Reach the illegal Alliance computer after the fourth assignment opens.
2. Navigate the restricted security and operations interface. Its visible
   branches include Repair, Supply, Air Defense, Ground Patrol, Security,
   Operation, Site Selector, transmitter control, and ship checks.
3. Complete the repair and authorization states needed to make the main
   computer operational. The interface reports four bombs loaded and exposes
   the ship only after its internal state has advanced.
4. Survive the room-security failures. Incorrect restricted access reaches a
   fatal security response rather than a useful alternate route.

### Cockpit and bombing flight

1. Enter the cockpit and install Modules A through D at their four matching
   control positions. The visible controls use button and slider prompts.
2. Complete the keypad/ship-control sequence. A wrong control can enter a death
   or retry branch; the valid sequence reaches logic 151.
3. Fly over each target region and press Enter to drop one bomb while the ship
   is inside the region's valid bounds. Each successful region sets one of the
   four completion flags.
4. Continue until all four completion flags are set and the flight reaches
   stage 12. The script then switches directly to logic 162.
5. Allow the ending cutscene to complete. `To be continued...` is the unique
   winning terminal marker for this evidence set.

## Required Inventory Ledger

| Item or state | Route role |
| --- | --- |
| MAD | Occupant records, tracking, notes, and travel |
| Key | Early locked-room access |
| Data Card | Report clue and suspect-name sequence |
| Crowbar | Central Park/later physical access chain |
| Keycard count and medallion | Progressive access state |
| Badge or badges | Selection and access chain |
| Modules A, B, C, D | Four independent cockpit installations |

Stuffed Orb and Stuffed Orbs are carnival prize states. Their exact necessity
on the shortest winning route remains to be confirmed by replay; they should
not be omitted from an exploratory capture merely because the terminal logic
does not test them directly.

## Deaths, Retries, and Dead Ends

- Tampering with the maintenance robot incorrectly allows it to self-destruct.
- Losing timed action scenes, knife/arcade sequences, or guard encounters enters
  the shared rewind presentation.
- Wrong paths in Central Park detonate mines.
- Incorrect badge, keycard, password, security, or cockpit choices can kill the
  player or return to an earlier checkpoint.
- The Alliance computer can eliminate an unauthorized user.
- Incorrect ship keypad actions and missed bomb regions prevent the ending.
- Reaching a visually advanced flight state with only one to three target flags
  is not a winning terminal state.

## Replay Work Still Required

The static evidence is sufficient to define the terminal contract and the
major dependency chain, but not yet a deterministic input file. A QEMU replay
must still record:

- exact movement coordinates and timing for each arcade room;
- the accepted suspect-name order for every report phase;
- the shortest valid carnival/keycard/badge route;
- the Alliance computer menu selections and cockpit control order; and
- the flight path and frame windows for the four bomb drops.

Those observations should refine this chapter without weakening the proven
terminal predicate above.
