# King's Quest 2 Playthrough Analysis

This chapter records a game-specific, clean-room reconstruction of a maximum-
score winning playthrough for the local `KQ2` evidence set. It is intended to
become a repeatable conformance scenario, not part of the portable AGI engine
specification. The route was derived from canonical logic, vocabulary, object,
picture, and view resources without consulting an external walkthrough.

The result is currently a **static candidate route**. The resources establish
a complete route to the wedding, an exact route to the declared maximum of
185, and a possible repeatable bridge award that could raise a winning score
to 191. Exact movement, random-character avoidance, bridge overscoring, and the
terminal input stream still require replay under the original interpreter.

## Evidence Method

The reusable playthrough index can be generated with:

```bash
AGI_GAME_DIR=games/KQ2 \
  python3 -B tools/logic_playthrough_index.py \
  --output build/playthrough/kq2/index.json
```

The index contains 133 readable logic resources, 1,406 parser conditions, 290
room transitions, 82 score mutations, and 85 inventory slots. Slots 50 through
84 contain 35 named objects; the earlier slots are unnamed placeholders. No
logic resource failed to decode. Logic 180 assigns **185** as the declared
maximum score.

The 222-point raw positive-site sum is not a reachable total. It includes
alternate trident, snake, candle, Dracula-key, lion, and recovered-treasure
branches. It also counts the ring and cloak award twice even though a shared
one-time state permits only one of those sites to add points. Conversely, the
raw sum cannot assign values to two variable awards: three points reserved for
the Dracula resolution and five points awarded on first reaching Valanice.

A direct renderer sweep produced all 108 present picture resources without an
error. The contact sheet corroborates the Kolyma forest and coast, magic door
and bridge, Neptune's underwater kingdom, mountain cave, Dracula's castle,
dwarf and Hagatha interiors, iridescent final sea, island, and quartz tower.

## Winning State

King Graham sees Valanice imprisoned in a quartz tower through the magic
mirror. A magic door in Kolyma requires three successive gold keys. Its
inscriptions direct Graham toward an underwater quest, a high-altitude quest,
and a final quest requiring a stout heart.

After opening all three doors, Graham reaches an iridescent sea, rescues a
golden fish, reaches the quartz tower, pacifies its lion, and finds Valanice.
Using the amulet's `home` command in Valanice's room selects logic 107 rather
than the bride-less ending. A monk declares Graham and Valanice married and the
game congratulates Graham for winning her hand. The declared-max conformance
scenario must reach this terminal sequence with score 185.

## Maximum-Score Principles

- Return Little Red Riding Hood's full basket. Eating its contents subtracts
  two points and prevents the four-point exchange for the bouquet.
- Give the bouquet to the mermaid. Giving ordinary treasure removes seven
  points; giving Neptune's trident removes three and destroys the sea route.
- Return the trident to Neptune for four points. Waving it personally opens the
  same clam for only two points, and the shared opened-clam state prevents both
  awards from coexisting on a surviving route.
- Transform the snake with the bridle for five points, then speak to the winged
  horse for two. Killing the snake with the sword awards only two.
- Cover Hagatha's nightingale cage with the bottle cloth before taking it.
  Returning the covered bird earns the lamp without surrendering two seven-
  point treasures. Opening the cage loses two points and the bird.
- Wear both the ruby ring and black cloak. The second item completing the
  disguise awards three points; a shared one-time flag means the two apparent
  three-point sites are not cumulative.
- Pray respectfully, identify Graham by name, and wear the monk's cross. The
  cross protects against awake Dracula, but the maximum route still kills the
  sleeping vampire with the stake and mallet.
- Feed the smoked ham to the lion for four points. Killing it gives two points
  and later subtracts three, for a net loss of one.
- Rescue the live golden fish. Killing it, letting it suffocate, or exploiting
  its corpse loses the route to the tower.
- Avoid the roaming dwarf. Each stolen seven-point treasure can be recovered
  from his trunk for seven points, making the detour score-neutral rather than
  an additional award.

## Candidate Route

Many Kolyma collections can be reordered. The sequence below keeps the three
gold keys separate because they occupy the same inventory slot and each must be
consumed at the magic door before the next is acquired.

### Kolyma preparations

1. At Grandma's cottage, open the mailbox and take the basket of goodies. Do
   not eat from it. Find Little Red Riding Hood and return the basket to receive
   her bouquet of wildflowers.
2. Search the opening at the base of the pond boulders and take the brooch.
   Move the clamshell on the beach and take the bracelet revealed beneath it.
3. Collect the stake leaning against a tree, the rusty trident in the grass,
   the necklace inside the hollow log, and the mallet in the pine-tree hole.
4. Enter the monastery chapel, kneel at the altar, and pray. When the monk asks
   Graham's name, answer `Graham`. Accept and wear his silver cross.
5. Enter the dwarf's underground house when it can be searched safely. Take
   the pot of chicken soup and open the trunk to take the earrings. Avoid the
   dwarf's roaming theft sequence.
6. Give the soup to sick Grandma, then look under her bed. Take the ruby ring
   and black cloak and wear both. Only the second disguise item awards the
   shared three-point completion bonus.
7. Cross the rickety bridge once on the declared-max route. Complete the
   traversal rather than merely entering the bridge room.

These preparations contribute **61** points.

### First gold key: make a splash

1. Give the bouquet to the mermaid and ride the magic seahorse she summons.
   The seahorse carries Graham underwater and supplies the breathing state
   needed to survive there.
2. Approach Neptune and give him his rusty trident. He gives Graham a bottle
   and uses the trident to open the giant clam. Do not wave the trident first.
3. Take the first gold key from the clam. Open the bottle and pull out the large
   cloth.
4. Return to the magic door and unlock its first stage. The key disappears and
   reveals the inscription for the high-altitude quest.

The sea quest contributes **15** points and the first door contributes **7**.
Cumulative score: **83**.

### Nightingale, lamp, and second gold key

1. Enter Hagatha's cave without alerting her. Drape the bottle cloth over the
   nightingale's cage before taking the covered cage. Leave without opening or
   uncovering it.
2. Give the covered nightingale to the antique-shop owner. She awards the old
   oil lamp without taking any treasure.
3. Rub or pat the lamp three times. Its genie successively leaves a magic
   carpet, sword, and leather bridle; each successful appearance awards two
   points. Ride the carpet once for four points.
4. Reach the snake guarding the high route. Throw the bridle onto the live
   snake rather than attacking it. Speak to the transformed winged horse and
   take the magic sugar cube it offers.
5. Eat the sugar cube before passing the poisonous brambles. Reach the damp
   cave and take the second gold key from the rock.
6. Return to the magic door and unlock its second stage.

The nightingale and lamp chain contributes **25** points; the winged-horse key
quest contributes **13**; and the second door contributes **7**. Cumulative
score: **128**.

### Third gold key: stout heart

1. Use the ring-and-cloak disguise to secure passage with the ghoul across the
   poisoned lake without paying a seven-point treasure. Keep the silver cross
   equipped for Dracula encounters.
2. In Dracula's castle, open the dresser and take the candle. Light it from one
   of the two reachable wall torches; the shared lit-candle state means the two
   one-point sites are alternatives. Take the smoked ham from the dining room.
3. Find Dracula asleep in his coffin. Put the stake on his chest and pound it
   with the mallet. The resolution awards four explicit points plus the
   remaining three-point Dracula bonus.
4. Take both the gold and silver keys left in or revealed by the coffin. The
   separate one-key and both-key parser branches are alternate ways to receive
   the same five- and two-point awards.
5. Use the silver key on the tower chest, open it, and take the tiara. Preserve
   the smoked ham for the final-world lion.
6. Return to the magic door and use the third gold key. The door reveals the
   iridescent world beyond it.

The castle quest contributes **27** points and the third door contributes
**7**. Cumulative score: **162**.

### Golden fish, Valanice, and wedding

1. On the blue beach, take the fishing net. Cast it from the accepted shoreline
   position to catch the golden fish, then take the gasping fish.
2. Throw the live fish back into the sea. Accept its offered ride and approach
   it when it calls. The beach sequence contains five guarded awards totaling
   eight points: net 1, catch 2, rescue 3, boarding 1, and completed ride 1.
3. On the strange island, take the bronze amulet. Traverse the quartz tower and
   give the smoked ham to the hungry lion. It eats and falls asleep, allowing
   Graham through the guarded door.
4. Enter Valanice's room. First arrival consumes a reserved five-point bonus.
   With Valanice rescued and the amulet still carried, say `home`. This awards
   three points and enters the wedding ending in logic 107.

The final world contributes **23** points. Final declared score: **185**.

## Score Ledger

| Phase | Selected awards | Phase total | Cumulative |
|---|---|---:|---:|
| Kolyma preparations | Mailbox/basket 3; return basket 4; brooch 8; bracelet 7; stake 2; trident 3; necklace 7; mallet 2; monastery/cross 6; soup/earrings 9; Grandma/disguise 9; bridge 1 | 61 | 61 |
| First key | Mermaid/seahorse 4; Neptune/trident 4; key 5; bottle cloth 2; first door 7 | 22 | 83 |
| Lamp and second key | Covered bird/lamp/genie/carpet 25; bridle/horse/cube/key 13; second door 7 | 45 | 128 |
| Third key | Candle/ham 5; Dracula resolution 7; keys 7; chest/tiara 8; third door 7 | 34 | 162 |
| Final world | Fish sequence 8; amulet 3; first Valanice arrival 5; ham solution 4; `home` 3 | 23 | **185** |

The exact equation can also be recovered from all immediate positive sites.
Starting from 222, exclude mutually exclusive sites worth 45 points: personal
trident wave 2, sworded snake 2, duplicate candle site 1, duplicate Dracula-key
branches 7, four score-neutral treasure recoveries 28, sworded lion 2, and the
second apparent disguise-completion site 3. The resulting 177 immediate points
plus variable bonuses of 3 and 5 equal 185.

## Bridge Overscore Hypothesis

Logic 48 does not guard its one-point bridge award with a permanent one-time
flag. Completing a traversal increments a counter, awards one point, and clears
the two side markers so another traversal can score. The fatal check uses
`counter > 6` before initiating the collapse, which appears to allow seven
successful awards and make an eighth attempt fatal.

The declared route above uses one bridge award. If the other six can be farmed
and Graham can leave the bridge on the useful side, the terminal score would be
**191** while the displayed maximum remains 185. Static control flow supports
this hypothesis, but exact collision rectangles, side selection, and the
ability to finish after the seventh traversal require original-interpreter
validation. Until then, 185 is the exact declared-max route and 191 is a
candidate actual maximum, not a promoted result.

## Deaths and Maximum-Score Dead Ends

- Eat the basket contents or return its empty remains to Little Red Riding
  Hood.
- Frighten the mermaid, pay her with treasure, or give her Neptune's trident.
- Dive without the magic seahorse or anger Neptune after keeping his trident.
- Attempt an eighth bridge crossing or fall from a cliff, staircase, carpet,
  or tower.
- Kill the snake instead of transforming it, or enter the brambles without the
  sugar-cube protection.
- Alert Hagatha by taking the uncovered singing bird, uncover it while still in
  the cave, or let her catch Graham.
- Buy the lamp with two treasures, open the birdcage, or lose scored treasure
  to the roaming dwarf.
- Enter the poisoned lake without safe transport; paying the ghoul with
  treasure also loses seven points.
- Traverse dark castle rooms without a lit candle, wake Dracula with the sword,
  approach him unprotected, or omit the stake or mallet.
- Kill the lion instead of feeding it, approach it too closely, or consume the
  ham earlier.
- Let the golden fish suffocate, kill it, throw back its corpse, or enter the
  turbulent sea without the rescued-fish ride state.
- Reach the ending without Valanice or consume the amulet before saying `home`
  in her room.

## Next Validation Work

1. Replay the bridge under the original interpreter and determine whether a
   winning 191-point terminal state is reachable.
2. Convert the 185 route, and the 191 route if confirmed, into exact movement,
   parser input, and timing streams.
3. Record room, inventory, key-stage, score, and terminal checkpoints at 61,
   83, 128, 162, and 185.
4. Confirm random dwarf, Hagatha, wolf, enchanter, Dracula, carpet, stair, and
   fish timing under the original interpreter.
5. Package the validated stream, screenshots, and ending assertions as a
   repeatable implementation-conformance playthrough.
