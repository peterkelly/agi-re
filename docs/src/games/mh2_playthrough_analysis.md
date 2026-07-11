# Manhunter: San Francisco Playthrough Analysis

This chapter is a fresh clean-room reconstruction of a winning route through
the replacement local `MH2` evidence set. It was derived from the current
game's logic, messages, vocabulary, object list, pictures, and views. It does
not reuse the earlier analysis of the incomplete copy, and no external
walkthrough or AGI documentation was consulted.

The result is a **static route specification**. The complete replacement input
now exposes the late game that was absent from the former copy: the Rat and Orb
item chain, the lava/slave controller, helicopter sequence, final control-room
puzzle, wraparound movement maze, and ending. Their state dependencies and
terminal edge are source-proven. Exact movement and a complete
original-interpreter replay remain future work.

## Evidence Method

The reusable index for this analysis was generated with:

```bash
AGI_GAME_DIR=games/MH2 \
  python3 -B tools/logic_playthrough_index.py \
  --output build/playthrough/mh2-replacement/index.json
```

The selected game uses interpreter 3.002.149 and the v3 combined resource
layout. All 96 present logic resources decode. The game also contains 248
pictures, 181 views, and 193 valid script-addressable sounds. Every resource
reference made by readable logic resolves. Two unreferenced sound-directory
tail entries select an absent volume and are inert for valid gameplay.

The analysis traced every inventory mutation, room switch, recognized full
name, assignment phase, and incoming terminal edge. Representative ending
pictures were rendered locally and corroborate San Francisco, the antagonist,
the Orb ship, and the ending montage. They are qualitative scene checks; logic
control flow supplies the ordering evidence.

No script assigns or changes a conventional numerical score or maximum-score
value. Winning is therefore defined by the unique continuation ending rather
than a points total.

## Story and Terminal State

The story continues with a Manhunter operating in Orb-controlled San
Francisco. Two explicit assignments direct the player to a burning boat at
Pier 5 and a human displayed on the sign at Ghirardelli Square. The MAD
database and tracker connect named occupants to Pier 5, Ghirardelli Square,
Chinatown, and the Alliance computer. The investigation expands into Rat
prizes and disguises, a historical Orb-on-a-Stick sequence, an Orb access
card, captive humans, lava controls, a helicopter flight, and a final Orb
facility.

Logic 187 is the winning terminal sequence. It has no outgoing room transition
and displays `To be continued...`. Its only incoming edge is from logic 183.
The edge requires:

- the maze to be in active movement phase;
- maze state 4;
- player X strictly between 129 and 144; and
- player Y less than 24.

Thus the player must reach the narrow top exit while the maze is in state 4.
Merely touching the top boundary in another state wraps the player elsewhere
and does not end the game.

## Global Route Constraints

1. Take both the ID Card and MAD in the opening sequence. The MAD provides the
   occupant database, tracker, notes, and travel interface used by the two
   assignments.
2. Keep state-bearing evidence until its explicit use: the Rat's Paw, ring,
   flask, Rat Mask 1, hatchet, statue, Orb Card, and Orb-on-a-Stick all have
   later consumption or access checks.
3. Prize choices are not equivalent. Rat Mask 1 is explicitly consumed in the
   late chain; selecting only Rat Mask 2 does not satisfy that check.
4. Preserve the Full Flask until the same late sequence that consumes Rat Mask
   1. Entering its dependent scene with a broken or missing flask reaches an
   explicit restore/death warning.
5. Do not lose the Orb Card before the cell-access sequence. The game can
   remove and later reacquire it, but the access machine still requires the
   appropriate card state.
6. Treat the many `back up a few minutes` branches as failures. They are useful
   retry checkpoints, not alternate progress paths.

## Assignments and Name Input

The assignment controller advances a small phase value and presents two
observable orders:

| Order | Assignment |
| ---: | --- |
| 1 | Investigate the burning boat at Pier 5 |
| 2 | Investigate the human on the Ghirardelli Square sign |

Reports request full names and parse them through the MAD occupant database.
Recognized names are Peter Brown, Noah Goring, Mic Stone, Tad Timov, and Zac
West, with spelling variants in the vocabulary. The records associate targets
with the Bank of Canton, Ghirardelli Square, Pier 5, and the Alliance computer.
As in the New York game, recognition and correctness are separate: individual
names set evidence flags, while assignment phase decides whether a resulting
branch advances or punishes the player. Exact report-answer order remains a
replay validation item.

## Candidate Winning Route

### Opening and city investigations

1. Start the game and take the ID Card and MAD in logic 124.
2. Accept the Pier 5 assignment. Use the MAD records and tracker to inspect the
   available named occupants and travel to the tracked location.
3. Complete the burning-boat investigation, collect its evidence, and return
   through the report sequence rather than a fatal or premature exit.
4. Accept the Ghirardelli Square assignment and investigate the human on the
   sign. Continue through the report and home-order sequences until the later
   city locations become available.

### Evidence and tool chain

The complete route draws on several city puzzles. Their proven inventory
effects are:

| Item | Acquisition | Later dependency |
| --- | --- | --- |
| Ring | Logic 132 movement room | Consumed in logic 168 |
| Rat's Paw | Logic 133 | Consumed by the associated Rat chain |
| Empty Flask | Earlier city room | Filled to become Full Flask in logic 136 |
| Rat Mask 1 | First row of the Three Aces prize logic | Consumed in logic 164 |
| Hatchet | Logic 165 | Used in logics 165 and 175 |
| Statue | Logic 128 | Consumed in the access chain in logic 176 |
| Orb Card | Logic 147 | Required and transformed around logics 176/179 |
| Orb-on-a-Stick | Logic 170 | Central late-story evidence |

1. Complete the movement rooms that yield the ring and Rat's Paw.
2. Obtain the Empty Flask and fill it during the laboratory/evidence sequence,
   producing the Full Flask.
3. Win the Three Aces game and choose Rat Mask 1 from the first prize row. The
   first row offers Flashlight, Rat Mask 1, and Key; the second offers Lantern,
   Rat Mask 2, and Medallion. Additional play may supply another prize, but
   Rat Mask 1 is the source-proven route requirement.
4. Acquire the statue and Orb Card. The card scene presents Orb propaganda and
   a direct take-card action; retain the resulting access state.
5. Follow the Rat Mask 1 and Full Flask branch in logic 164. Both items are
   removed by separate local states, proving that the scene requires more than
   simply entering the room.
6. Take the hatchet in logic 165 and use it where the next sequences consume
   it. Follow the girl/inside transitions rather than leaving the chain.
7. Use the ring in logic 168. That route switches directly to logic 170, where
   the historical `July 2001` scene makes the Orb-on-a-Stick available.
8. Take the Orb-on-a-Stick and continue through the outside/inside chain in
   logics 172 and 175.

### Orb access and captive route

1. Reach the cell-door access machine in logic 176. It displays `SCANNING`,
   then either `ACCESS DENIED...ELIMINATE!` or `ACCESS APPROVED`.
2. Supply the required statue/card state. The logic removes the statue in one
   access phase and manipulates the Orb Card in later phases; an absent or wrong
   access item follows the elimination branch.
3. Continue into the Orb facility rather than returning to an earlier city
   room. Subsequent rooms lead to the lava, robot, and captive-human control
   board.

### Lava, robots, and slaves

Logic 178 implements a board with visible locations and states labelled
`Slavery`, `Hell - You are here`, `Freedom`, `Life`, and `The Digger`.
Controls move robots or slaves, open and close gates, and move lava between
sections. The script rejects any attempt to move robots or slaves into a
section flooded with lava.

1. Use the destination sensors to relocate lava away from a section before
   moving occupants into it.
2. Open only the gate needed for the current move, transfer the selected group,
   and close or reposition the gate before changing the lava layout.
3. Continue until the board's completion state enters logic 185. Numerous
   partial states return from logic 178 to logic 185; these are controller
   substeps rather than independent rooms.
4. In the connected late rooms, recover the Orb Card state when offered and
   follow the transitions through logics 179, 180, and 181. Logic 180 warns the
   player to save before the stuck-handle sequence.

### Helicopter and final facility

1. Logic 181 feeds into the helicopter game in logic 161. Press Enter for more
   lift while steering clear of the tower. A collision displays `You hit the
   tower!`; the successful route displays `You won!!!` and continues.
2. Return through the late controller in logic 185. Complete the button and
   limited-flash interactions until its phase reaches the transition to logic
   186.
3. Logic 186 arranges a row of seven controlled objects and tests a multi-step
   button sequence. Complete that sequence, then enter its lower target region;
   the script assigns the next room as logic 183.

### Final wraparound maze

Logic 183 is a toroidal movement puzzle. The arrow directions change when the
player crosses an edge:

| Edge crossed | Incoming directions | Wrapped destination and new direction |
| --- | --- | --- |
| Top | 1 or 2 | Bottom; 1 becomes 3, 2 becomes 4 |
| Bottom | 3 or 4 | Top; 3 becomes 1, 4 becomes 2 |
| Right | 1 or 3 | Left; 1 becomes 2, 3 becomes 4 |
| Left | 4 or 2 | Right; 4 becomes 3, 2 becomes 1 |

1. Use the arrow keys to traverse the wraparound board and advance its internal
   maze state to 4.
2. In state 4, approach the top edge with X between 130 and 143 inclusive.
3. Cross above Y 24. The script switches immediately to logic 187.
4. Allow the ending montage to complete. `To be continued...` is the winning
   terminal marker.

## Other Inventory and Optional Branches

The object table also contains a Dragon Note, Newspaper, Scroll, Laundry
Receipt, Muzzle, Fang, Mallet, Driver's License, Cloth, Camera, two letters,
Matchbook, Walking Stick, Empty Gun, Flashlight, Lantern, Rat Mask 2, Key, and
Medallion. Several are required in earlier local puzzles even though the final
logic does not inspect them directly. The Matchbook is initialized or acquired
in logic 180, and the Walking Stick has a direct acquisition action in the
late-city chain.

Until a complete replay chooses and records every prize and side branch, these
items should be classified as route candidates rather than discarded as
optional solely from terminal reachability.

## Deaths, Retries, and Dead Ends

- Wrong report names can route to the shared failure/retry logic.
- Movement rooms around the ring and Rat's Paw contain fatal branches.
- Entering the late chain without the intact Full Flask triggers an explicit
  warning that continuing will kill the player.
- Choosing Rat Mask 2 instead of acquiring Rat Mask 1 leaves the source-proven
  late consumption check unsatisfied.
- Failed Orb-card scanning produces `ACCESS DENIED...ELIMINATE!`.
- Moving robots or slaves into lava is rejected; incorrect board states can
  strand the controller sequence.
- The stuck-handle sequence explicitly warns the player to save.
- Insufficient helicopter lift or lateral error hits the tower.
- Wrong final-control button sequences do not enter the maze.
- The maze's top edge is not an exit before state 4, or outside X 130..143.

## Replay Work Still Required

The replacement resource set proves a complete terminal route exists, but an
automated conformance replay still needs:

- exact report-name order for both assignments;
- the shortest city movement path and necessary side-item selections;
- the number of Three Aces wins and complete prize choice sequence;
- the exact lava/gate/robot/slave solution;
- helicopter steering and lift timing;
- the seven-object button solution in logic 186; and
- an arrow-key sequence that reaches maze state 4 and the narrow top exit.

QEMU observations should be used to resolve those inputs and to capture retry
behavior, while the static predicates above remain the source of truth for
what constitutes the winning terminal state.
