# Mixed-Up Mother Goose Playthrough Analysis

This chapter records a game-specific, clean-room reconstruction of a complete
winning playthrough for the local `MG` evidence set. It is intended to become a
repeatable conformance scenario, not part of the portable AGI engine
specification. The route was derived only from the game's logic, messages,
pictures, views, sounds, and state transitions. No external walkthrough or AGI
documentation was consulted.

Unlike the other games analyzed so far, *Mixed-Up Mother Goose* does not use a
traditional adventure score or inventory list. It randomly distributes
nursery-rhyme props around its map, lets the player carry one prop at a time,
and counts completed rhymes. A winning game completes all **18 of 18** rhymes.
The result below is a complete static strategy, but exact movement and a fixed
randomized starting layout still require original-interpreter replay.

## Evidence Method

The reusable logic index can be generated with:

```bash
AGI_GAME_DIR=games/MG \
  python3 -B tools/logic_playthrough_index.py \
  --output build/playthrough/mg/index.json
```

The selected game identifies itself as *Mixed-Up Mother Goose* and uses
interpreter 2.915. Its split directories contain 73 readable logic resources,
49 pictures, 100 views, and 53 sounds. The index found 159 explicit room
switches and only one named inventory-table entry, `?`; the game implements its
portable props through custom variables and animated objects instead of the
ordinary AGI inventory table. No present logic resource failed to decode.

Logic 0 assigns 18 as the displayed maximum and initializes the ordinary score
variable to zero. It increments that variable once after each successfully
completed rhyme animation. When the value reaches 18, it starts the completion
sequence in logic 102. Thus `18` is both the maximum displayed value and the
number of solved rhymes, rather than a sum of differently valued puzzle awards.

All 49 present pictures decoded in a qualitative sweep with patterned brushes
disabled. They corroborate the outdoor grid, cottages, castle, shoe house,
pumpkin house, school, barn and bedrooms, plus the cloud-framed finale. These
renders are geographical evidence rather than pixel-conformance evidence.

## Runtime Game Model

### Map

Rooms 1 through 35 form a regular outdoor grid of seven columns and five rows:

```text
 1  2  3  4  5  6  7
 8  9 10 11 12 13 14
15 16 17 18 19 20 21
22 23 24 25 26 27 28
29 30 31 32 33 34 35
```

The edges generally connect north, east, south, and west to the corresponding
neighbor. Nine special interiors or enclosed scenes branch from this grid:

| Exterior | Attached room |
| ---: | ---: |
| 4 | 37 |
| 10 | 36 |
| 12 | 38 |
| 13 | 39 |
| 15 | 40 |
| 21 | 44 |
| 24 | 41 |
| 26 | 43 |
| 32 | 42 |

The exact doorway trigger is positional, so a replay must record coordinates
as well as room numbers.

### Randomized props

A new game creates a shuffled placement of twenty props. Logic 0 repeatedly
chooses eligible rooms, rejects occupied or disallowed combinations, and stores
one prop in each accepted room. Consequently, there is no single fixed sequence
such as “go to room 8 for the pail.” The player must explore the map, recognize
visible props, and either deliver each immediately or remember its room.

The player carries at most one prop. Approaching a loose prop transfers it into
the carried-prop state; approaching the correct rhyme character with that prop
starts the corresponding completion logic. A wrong prop does not increment the
completion count. Most successful deliveries consume one prop. Old King Cole
is the exception: his one rhyme requires three deliveries in a fixed sequence.

### Completion protocol

Each correct final delivery performs the same observable sequence:

1. Player control is suspended and the relevant rhyme animation begins.
2. The full nursery rhyme is displayed while its sound and character animation
   run.
3. The rhyme logic signals that its animation has finished.
4. Logic 0 waits for the common sound/animation completion state, increments
   the solved-rhyme count exactly once, clears the temporary carried-prop and
   interaction state, and returns control.
5. After the eighteenth increment, normal exploration is replaced by the
   finale.

This sequencing matters to a compatible implementation: the counter changes
after the completion presentation, not at the first moment the correct prop is
recognized.

## Rhyme and Prop Table

The complete winning condition is one completion for every row. The numeric
prop identifiers are included as evidence labels for this game-specific route;
they are not portable AGI inventory numbers.

| Recipient or rhyme | Room logic | Required prop | Prop id |
| --- | ---: | --- | ---: |
| Jack and Jill | 1 | Pail | 26 |
| Little Tommy Tucker | 3 | Breadknife | 20 |
| Humpty Dumpty | 5 | Ladder | 29 |
| Cat and the Fiddle | 7 | Fiddle | 18 |
| Little Miss Muffet | 9 | Tuffet | 12 |
| Peter, Peter, Pumpkin-Eater | 12 | Wife | 11 |
| Mary Had a Little Lamb | 13 | Lamb | 17 |
| Crooked Man | 15 | Sixpence | 28 |
| Ride a Cockhorse | 18 | White horse | 30 |
| Old Woman Who Lived in a Shoe | 21 | Broth | 24 |
| Little Bo Peep | 23 | Sheep | 15 |
| Where Has My Little Dog Gone? | 27 | Dog | 16 |
| Mary, Mary, Quite Contrary | 31 | Watering can | 27 |
| Jack Be Nimble | 33 | Candlestick | 25 |
| Jack Sprat | 36 | Platter | 21 |
| Old King Cole, stage 1 | 37 | Pipe | 22 |
| Old King Cole, stage 2 | 37 | Bowl | 23 |
| Old King Cole, final stage | 37 | Fiddlers three | 14 |
| Hickory, Dickory, Dock | 41 | Mouse | 13 |
| Little Jack Horner | 43 | Pie | 19 |

The table has twenty prop rows but only eighteen completed rhymes because the
three Old King Cole rows contribute one completion together. His logic records
the pipe first, accepts the bowl only after the pipe, and accepts the fiddlers
only after both earlier stages. Delivering the fiddlers in the final state
starts logic 87 and contributes the single Old King Cole increment.

## Candidate Winning Strategy

### Start and survey

1. Start a new character, enter a name, and choose one of the available player
   appearances. A new character causes the prop layout to be randomized.
2. Traverse rooms 1 through 35 in a serpentine sweep: move east across one row,
   descend, move west across the next, and continue. Enter each of the nine
   attached rooms while passing its exterior.
3. Record every visible portable prop and its room. The twenty-prop table above
   supplies the eventual destination for each. Also note the fixed recipient
   rooms; their requests identify missing rhyme components on screen.

### Delivery loop

1. Choose any unsolved recipient other than Old King Cole, travel to the room
   containing its prop, approach the prop to carry it, then travel to the
   recipient room and approach the character.
2. Wait for the complete rhyme animation and sound. Do not begin the next
   movement sequence until normal control returns and the displayed count has
   advanced.
3. Repeat for the 17 single-completion rhymes. The order is otherwise free;
   completion logic is keyed by recipient and carried prop rather than a global
   story phase.
4. For Old King Cole in room 37, deliver the pipe, then the bowl, then the
   fiddlers three. The first two deliveries update his staged request but do
   not increase the solved-rhyme count. The fiddlers trigger the full rhyme and
   the one associated increment.
5. If a prop's original room is forgotten, repeat the systematic map sweep.
   Correctly completed props no longer participate in later loose-prop searches,
   so the remaining set becomes progressively smaller.

### Terminal sequence

After the eighteenth rhyme animation, logic 0 observes a solved count of 18,
suspends normal control, and starts the completion state. Logic 102 assembles
the nursery-rhyme cast into a multi-stage celebration, displays thanks using
the chosen player name, transitions to the going-home scene, and finally
displays:

> Mother Goose and her design team hope you enjoyed Mixed-Up Mother Goose.
> Congratulations on a job well done!

The finale then restores the status line but disables the ordinary save,
restore, restart, display, joystick, and speed menu entries. The congratulatory
scene with **18 of 18** completed rhymes is the winning terminal state used by
this analysis.

## Completion Ledger

| Completion class | Rhymes | Counter increase |
| --- | ---: | ---: |
| Single-prop rhymes | 17 | 17 |
| Old King Cole after pipe, bowl, and fiddlers | 1 | 1 |
| **Total** | **18** | **18** |

There are no higher-valued actions or optional bonus points. The conventional
one-point increment found by the generic index is the shared post-animation
increment in logic 0, executed once for each completed rhyme.

## Failure and Recovery Model

- The decoded game contains no adventure-style death sequence or negative
  score operation. Exploration can be repeated indefinitely.
- Taking a prop to the wrong recipient does not enter that recipient's
  completion branch and does not increase the solved count.
- The one-prop carrying limit means another prop cannot be collected until the
  current one is delivered or otherwise released through the normal object
  interaction.
- Old King Cole cannot be completed out of order. The bowl depends on the pipe
  stage, and the fiddlers depend on both earlier stages.
- Stopping during a completion animation can make an automated replay lose
  synchronization even though game state is not lost. A harness must wait for
  the count increment or restored player control.
- Save and restore provide recovery from an interrupted survey. Because the
  randomized placement belongs to game state, a fixed save is also the simplest
  way to make the eventual compatibility replay deterministic.

## Replay Work Remaining

1. Create one original-interpreter save immediately after randomized placement
   and record the resulting prop-to-room map without committing the private save.
2. Record exact coordinates for collecting every prop, entering all nine
   attached rooms, and activating every recipient.
3. Capture checkpoints after each count increment, with special checks that
   Old King Cole remains unchanged after pipe and bowl and advances only after
   the fiddlers.
4. Verify wrong-recipient and repeated-recipient behavior with short targeted
   replays.
5. Run the complete 18-rhyme route under interpreter 2.915 and package its
   input stream, randomized-state description, counter sequence, and terminal
   frames as a deterministic game-level compatibility scenario.
