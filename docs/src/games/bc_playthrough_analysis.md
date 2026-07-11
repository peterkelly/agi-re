# The Black Cauldron Playthrough Analysis

This chapter records a game-specific, clean-room reconstruction of a maximum-
score winning playthrough for the local `BC` evidence set. It is intended to
become a repeatable conformance scenario, not part of the portable AGI engine
specification. The route was derived only from the game's logic, messages,
vocabulary, objects, pictures, and views. No external walkthrough or AGI
documentation was consulted.

The result is currently a **static candidate route**. The declared 230-point
maximum, all score alternatives, inventory dependencies, major transitions,
and terminal branches reconcile exactly. Exact movement, action-menu input,
hazard timing, and a complete original-interpreter replay remain to be done.

## Evidence Method

The reusable playthrough index can be generated with:

```bash
AGI_GAME_DIR=games/BC \
  python3 -B tools/logic_playthrough_index.py \
  --output build/playthrough/bc/index.json
```

The game identifies itself as *The Black Cauldron*, version 2.00 dated June
14, 1987, and uses interpreter 2.439. Its split directories contain 85 readable
logic resources, 69 pictures, 178 views, and 28 sounds. The index found 21
parser predicates, 213 explicit room switches, 61 inventory mutations, 26
inventory slots, and 40 positive score operations. No present logic failed to
decode.

Logic 107 assigns **230** as the maximum score. The 40 award sites sum to 463
when mutually exclusive branches are counted together. Direct condition and
state analysis reduces that total to exactly 230:

- feeding Hen Wen corn or gruel shares one five-point state;
- two ledge directions, two mountain faces, and two castle-road screens share
  their respective five-, six-, and five-point completion states;
- the wagon and window castle entrances share one 18-point state;
- four methods of getting Hen Wen to safety are alternatives worth 20 points;
- three sword-assisted castle outcomes share one 13-point state;
- four dungeon escape discoveries share one six-point state;
- three first meetings with Eilonwy share one ten-point state;
- an apple or cookies makes Gurgi a friend for the same ten points;
- the three secret-chamber sacrifices/resolutions are alternatives; and
- the two final rewards are alternate 15-point endings.

All 69 present pictures decoded in a qualitative sweep with patterned brushes
disabled. The resulting sheet corroborates Caer Dallben, the forest and river,
the Eagle Mountains, the castle exterior and interior, its dungeon and hidden
passages, the Fair Folk dwellings, Morva Marsh, and the witches' house. Because
the brush-disabled renders are not pixel-conformance evidence, they are used
only to check geography and scene identity. A later audit maps BC's v2 mask
and pointer tables at `0x1575` and `0x1595`; this does not retroactively turn
the historical disabled-brush sheet into conformance evidence.

## Story and Winning State

Taran begins as Assistant Pig-Keeper at Caer Dallben. Hen Wen's visions could
reveal the Black Cauldron to the Horned King, so Dallben sends Taran to place
her with the Fair Folk. The maximum route also befriends Gurgi, enters the
Horned King's castle, explores its dungeon and passages, frees Fflewddur Fflam,
finds the magic sword Dyrnwyn, reaches the Fair Folk king, and trades Dyrnwyn
to the witches for the Black Cauldron.

The cauldron ultimately reaches the Horned King's secret chamber. In the
selected resolution Taran holds the Fair Folk's mirror before the Horned King.
The king sees his evil self, leaps into the cauldron, and destroys himself and
the Cauldron-Born threat. The witches then offer Taran several rewards for the
now-powerless cauldron. Selecting the returned magic sword adds the final 15
points and enters ending logic 71.

Logic 71 computes a congratulatory threshold of maximum minus 15, or 215. The
selected reward raises the score from 215 to **230 of 230**, so the ending
displays `Congratulations!! You've played a tremendous game!!`. This is the
maximum-score terminal state used by this analysis.

## Global Constraints

1. Feed Hen Wen either corn or gruel before beginning the quest. The two
   actions are alternative realizations of the same five-point award.
2. Take the knapsack, rope, water flask, bread, and apple from Dallben's area.
   Hunger and thirst progress during play and can become terminal; carry food,
   refill the flask only from safe water, and eat and drink before the final
   warnings expire.
3. Take the lute from the forest tree and the dagger from the no-trespassing
   sign. Preserve one instrument for King Eiddileg, the dagger for vines or
   ropes, and Dyrnwyn for the witches.
4. Befriend Gurgi with either the apple or Gwystyl's cookies. The two gifts are
   alternatives and both set the state needed for later Gurgi scenes.
5. Place Hen Wen with the Fair Folk exactly once. The selected route uses
   Gwystyl; the drawbridge, parapet, and Eilonwy routes are alternate 20-point
   solutions and cannot be added to it.
6. Learn and retain Gwystyl's password, **bmmpxf**. It opens the concealed
   waterfall route to the Fair Folk realm.
7. Give either the lute or Fflewddur's harp to King Eiddileg. Both gifts enter
   the same ten-point branch and yield the magic mirror and flying dust.
8. Keep the mirror. Offering it to the witches prevents transformation but is
   insufficient to buy the cauldron; Dyrnwyn completes that bargain. The
   mirror is then the highest-valued secret-chamber resolution.
9. Obtain only one award from each shared mountain, castle-entry, dungeon-clue,
   and Eilonwy-introduction group. Revisiting their alternate locations does
   not increase the score.
10. Do not accept the witches' book, gold, shield, or armor endings. They end
    Taran's adventure below the selected maximum. After the Horned King is
    defeated, continue rejecting offers until Dyrnwyn is offered.

## Candidate Route

### Caer Dallben and the Fair Folk way station

1. At Dallben's cottage, take the knapsack, water flask, bread, apple, and
   gruel. At Hen Wen's shed, open the attached shed and take the corn. Feed Hen
   Wen either the corn or gruel for five points, then return to Dallben so her
   vision starts the quest. Take the rope Dallben supplies.
2. Search the nearby world before committing to the long journey. Take the
   food wallet from beneath the bridge, the lute from the hollow tree, and the
   dagger holding the no-trespassing sign.
3. Meet Gurgi and give him the apple. He becomes Taran's friend for ten points.
   The cookies found shortly afterwards are an equivalent alternative and need
   not be consumed for score.
4. Lead Hen Wen through the overgrown briar path. Reaching the concealed
   clearing awards four points. Enter Gwystyl's way station and let him take
   Hen Wen through the Fair Folk passage. His conversation awards 20 points,
   confirms her safety, and supplies the password `bmmpxf`. Open his cupboard
   and take the cookies if they are needed as food.

### Fair Folk and the Eagle Mountains

1. Reach the waterfall, use the magic word, and enter the revealed cave. The
   descent reaches King Eiddileg's hidden realm and awards 13 points.
2. When Eiddileg asks for proof that Taran represents Dallben, give him the
   lute. The gift awards ten points. Keep the magic mirror and flying dust that
   he supplies.
3. Travel toward the Eagle Mountains. At the vertical rock wall, use the rope
   on the dead branch and complete one scored ledge transition. Continue across
   one of the paired mountain-face routes, then onto one of the paired castle
   road screens. The three shared groups award 5, 6, and 5 points, in addition
   to the five-point first arrival at the rock-wall sequence.
4. Keep the dagger usable while crossing the mountain. Unsafe reaches, letting
   go of the rope at the wrong time, or stepping from the ledge cause a fatal
   fall; scraping the dagger on rock also dulls it.

### Castle, dungeon, and Dyrnwyn

1. At the castle approach, hide in the henchman's wagon. Riding through the
   gate awards the selected 18-point castle-entry branch. Avoid the moat and
   alligators.
2. Explore the courtyard, halls, and dungeon. Take the ring of keys, then use
   it to open the locked cells and free Fflewddur Fflam. Freeing him awards
   nine points and makes his harp available, although the selected route has
   already given Eiddileg the lute.
3. Enter the prison-cell and hidden-passage sequence. Use the tin cup against
   the door or floor to expose the loose flagstone; this is the selected
   six-point dungeon-clue branch. Meet Eilonwy through that opening for the
   single ten-point introduction award and follow her into the passages.
4. Push the loose wall blocks until the route into the burial chamber opens,
   earning ten points. In the king's tomb, take Dyrnwyn from the carved stone
   king for eight points. Preserve the sword for Morva Marsh.
5. Return through the dungeon and castle. Use Dyrnwyn on the drawbridge chain,
   or leave by the old window while carrying it, to claim the single 13-point
   sword-assisted escape award. The selected replay should use one branch and
   record it explicitly; the shared flag prevents scoring both.

### Morva Marsh and the Black Cauldron

1. Cross the swamp by jumping only onto stable rocks and logs. Reach the hidden
   area outside the witches' house for the 15-point Morva arrival award.
2. Enter the house and confront Orddu, Orwen, and Orgoch. The mirror prevents
   the immediate frog ending but does not buy the cauldron. Offer Dyrnwyn when
   the item choice becomes available. The witches accept the sword, award 18
   points, and place the Black Cauldron outside.
3. Keep the cauldron from the gwythaint as long as the current sequence permits.
   The story eventually carries the cauldron toward the Horned King's castle;
   follow the resulting route back to the secret chamber.

### Horned King and maximum ending

1. In the secret chamber, act before too many skeletons emerge. Select and use
   the magic mirror on the Horned King. He sees his true nature and leaps into
   the cauldron. This is the selected 25-point resolution; jumping personally
   or allowing Gurgi to sacrifice himself are alternate score branches.
2. Survive the castle's collapse and the moat escape. The ending returns Taran
   and the powerless cauldron to the lake where the witches bargain for it.
3. Reject the book of knowledge, pot of gold, warrior's shield, and suit of
   armor. Accept Dyrnwyn when the witches finally offer to return the magic
   sword. This awards the final 15 points and enters the congratulatory ending
   at **230 of 230**.

## Score Ledger

The ledger deliberately selects one member of every shared alternative group.

| Chain | Points |
| --- | ---: |
| Feed Hen Wen corn or gruel | 5 |
| Reach Gwystyl's concealed clearing | 4 |
| Deliver Hen Wen to Gwystyl | 20 |
| Befriend Gurgi with apple or cookies | 10 |
| Enter King Eiddileg's realm | 13 |
| Give Eiddileg the lute or harp | 10 |
| Rock-wall arrival and ledge traversal | 10 |
| Complete one mountain-face route | 6 |
| Complete one castle-road route | 5 |
| Enter the castle by wagon | 18 |
| Obtain one dungeon escape clue | 6 |
| Meet Eilonwy | 10 |
| Open the hidden passage | 10 |
| Free Fflewddur Fflam | 9 |
| Take Dyrnwyn | 8 |
| Complete one sword-assisted castle outcome | 13 |
| Reach the hidden Morva area | 15 |
| Trade Dyrnwyn for the Black Cauldron | 18 |
| Defeat the Horned King with the mirror | 25 |
| Recover Dyrnwyn in the final bargain | 15 |
| **Total** | **230** |

## Alternate Winning Branches

The 230-point arithmetic is not tied to every physical choice above. The
logic deliberately makes several routes score-equivalent:

- Hen Wen can reach safety through Gwystyl, the castle drawbridge, the
  parapet, or Eilonwy's tunnel; each realization contributes 20 points.
- The wagon and old-window castle entries share the 18-point award.
- Multiple dungeon discoveries can reveal an escape route, but the first is
  worth six points and suppresses the rest.
- Eilonwy can first appear in three nearby passage/cell contexts; only the
  first meeting awards ten points.
- The drawbridge, window, and secret-chamber sword checks share one 13-point
  state.
- In the secret chamber, the mirror and Taran's own sacrifice are worth 25
  points, while Gurgi's sacrifice is worth 20. Lower-valued resolution paths
  require a compensating story branch or finish below the maximum.
- The final 15-point reward is either Dyrnwyn when Gurgi lives or Gurgi's
  return after his sacrifice. These outcomes are mutually exclusive.

These alternatives should eventually become separate replay scenarios. The
selected route above is useful because its score ledger is simple and keeps
both Gurgi and Taran alive.

## Failure and Dead-End Map

- Starvation and dehydration become terminal if their warning sequences are
  ignored. Rapids can also tear away the flask or drown Taran.
- Leaving Hen Wen exposed allows a gwythaint or the Horned King's forces to
  capture her. If she reveals the cauldron's location, evil wins.
- Bog tiles, unsafe ledge moves, rope mistakes, mountain falls, and the castle
  moat kill Taran immediately.
- Entering the castle openly, waiting near henchmen, or failing timed escapes
  leads to capture. Some captures are recoverable dungeon routes; others let
  the Horned King win.
- The cook, throne-room observers, gwythaints, falling stones, alligators, and
  released Cauldron-Born impose movement or timing failures.
- Releasing the witches' prisoners without a viable bargain can transform
  Taran into a frog or trap him in the chest.
- Accepting a lesser final reward is a terminal but non-maximum conclusion.
- Allowing too many skeletons to emerge in the secret chamber ends the game,
  so the mirror action must be selected promptly.

## Replay Work Remaining

1. Record exact action-menu and active-object input for every non-movement
   step, especially feeding, the waterfall password, dungeon interactions,
   the witches' bargain, mirror use, and final reward selection.
2. Resolve the exact movement coordinates and timing for swamp jumps, rope and
   ledge traversal, wagon entry, dungeon routes, castle escape, and the secret
   chamber.
3. Validate that the selected ordering can collect every common score group
   without an unnoticed phase-state exclusion; checkpoint after 5, 39, 62,
   83, 157, 190, 215, and 230 points.
4. Run the complete route under interpreter 2.439 with the patched VGA BIOS and
   capture score, room, inventory, Hen Wen/Gurgi state, and ending frames.
5. Package the validated input stream and checkpoints as a deterministic
   game-level compatibility scenario, then add shorter replays for the
   score-equivalent rescue and ending branches.
