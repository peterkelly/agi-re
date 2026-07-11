# King's Quest 3 Playthrough Analysis

This chapter records a game-specific, clean-room reconstruction of a maximum-
score winning playthrough for the local `KQ3` evidence set. It is intended to
become a repeatable conformance scenario, not part of the portable AGI engine
specification. The route was derived from canonical logic, vocabulary, object,
picture, view, and locally supplied spell-text resources without consulting an
external walkthrough.

The result is currently a **static candidate route**. Logic control flow,
messages, parser vocabulary, inventory transformations, score mutations, and
room transitions support a complete 210-point route. Exact movement, wizard
and pirate timing, mountain navigation, and the final input stream still
require replay under the original interpreter.

## Evidence Method

The reusable playthrough index can be generated with:

```bash
AGI_GAME_DIR=games/KQ3 \
  python3 -B tools/logic_playthrough_index.py \
  --output build/playthrough/kq3/index.json
```

The index contains 125 readable logic resources, 2,994 parser conditions, 277
room transitions, 67 score mutations, and 55 inventory slots. No logic failed
to decode. Logic 101 assigns **210** as the declared maximum score.

All positive score sites total 215. Logic 14 contains two four-point position
branches for completing the same spider-removal sequence, guarded by one
completion flag. Logic 39 likewise accepts `pet dog` and `get dog hair` as
alternate one-point parser routes to the same inventory state. Removing the
duplicate four- and one-point sites gives exactly 210. No negative score action
is present, so maximum play depends on collecting every intended award and
avoiding mutually exclusive duplicate counting.

The seven successful spell preparations are represented by separate one-time
flags and award ten points each. Their resulting inventory objects occupy
synthetic locations 121 through 127 before being collected or activated. The
local `SPELLS.TXT` supplies the exact recipes and empowering verses used below.

A direct renderer sweep produced all 97 present pictures without error. The
contact sheet corroborates Manannan's mountaintop house and laboratory,
Llewdor's forest, desert, village and bandit tree, the pirate ship, landing
beach, snowy mountain labyrinth, ruined Daventry, cloud-top dragon ground, and
restored castle ending.

## Story and Winning State

Seventeen-year-old Gwydion lives as the wizard Manannan's slave. He must use
the wizard's absences and sleep periods to discover a hidden laboratory,
collect ingredients, and prepare magic without being caught. A cat cookie
hidden in porridge transforms Manannan permanently and frees Gwydion.

The Oracle then establishes that Gwydion is Prince Alexander of Daventry and
that his sister, Princess Rosella, is about to be sacrificed to a three-headed
dragon. Alexander buys passage across the ocean, escapes the pirates, crosses
the mountains, kills the dragon with a magical storm, and frees Rosella.

Entering the castle hallway with Rosella awards the final four points and leads
to logic 74. King Graham and Queen Valanice welcome both children, the magic
mirror clears, Graham throws his adventurer's hat toward them, and the game
displays its completion congratulations. The conformance route must enter this
terminal sequence with score 210.

## Timed House State

Manannan cycles among four broad states: awake at home, away on a journey,
asleep, and returned hungry. He also assigns one of five chores: clean the
kitchen, empty the chamber pot, prepare food, dust the study, or feed the
chickens. Failure, forbidden-room discovery, visible ingredients, a missing
wand, or detected spellcraft can cause punishment, confiscation, or death.

The static route therefore follows these invariants until Manannan is
transformed:

1. Complete each assigned chore before its deadline.
2. Enter the bedroom, study, or laboratory only while Manannan is away or
   safely asleep.
3. Return the brass key to the closet top after opening the wand cabinet.
4. Replace the wand in the cabinet, relock it, close the trapdoor, and replace
   the concealing book before Manannan returns.
5. Hide all suspicious carried objects under Gwydion's bed before an
   inspection, then retrieve them during the next safe interval. The first
   successful bulk hiding awards four points.
6. Keep ordinary bread, fruit, or mutton available for early hunger cycles.
   Do not offer the poisoned porridge until the cat cookie is ready.

These rules define the safe state transitions; exact timer values and the
fastest deterministic schedule remain replay work.

## Candidate Route

### House tools and discoveries

1. Obey the opening order to sweep the kitchen. During safe intervals, climb
   to the telescope tower and take the dead fly's wings for one point.
2. Search Manannan's bedroom thoroughly. Search behind the closet contents for
   the magic map, feel along the closet top for the brass key, and search the
   vanity drawers for the hand mirror and rose-petal essence. These four
   discoveries award 7, 3, 1, and 1 points.
3. In the kitchen take the wooden spoon, knife, clay bowl, bread, fruit, and
   mutton for one point each. Take the tin cup from the dining-room table for
   another point.
4. In the study, move the large book and pull the hidden lever. This opens the
   trapdoor and awards five points. Use the brass key on the cabinet and take
   the wand only while actively performing spell work.
5. Descend to the laboratory for its four-point first discovery. Take the six
   required shelf ingredients, each worth one point: powdered fish bone,
   saffron, nightshade juice, mandrake-root powder, toadstool powder, and toad
   spittle.
6. Hide the accumulated contraband beneath Gwydion's bed before Manannan can
   inspect him. Preserve the four-point first-hide award while following the
   replacement rules above.

House tools and discoveries contribute **39** points.

### Llewdor ingredients and side quests

The following collections can be interleaved with safe house visits and spell
preparation:

1. Catch a chicken and pluck one small feather. Pluck hair from Manannan's cat.
   Each acquisition awards one point.
2. In the desert take the dried snakeskin and the unusual cactus for one point
   each. Defeat Medusa by averting Alexander's eyes and pointing Manannan's
   hand mirror at her; the reflection solution awards five points.
3. At the large oak, collect the dried acorns for one point and find the hidden
   rope to lower the ladder for three. Reach the bandit treehouse for two
   points. Later, while transformed into a fly, enter the root hole for another
   five-point discovery.
4. Listen to the bandits' tavern conversation until the treehouse clue completes
   for three points. Enter while the resident bandit sleeps and take the coin
   purse for four.
5. Pet the storekeeper's dog or explicitly take its fur. Either parser route
   awards the same single point. Buy salt, lard, fish oil, and an empty pouch
   for one point each. Make all four purchases before surrendering the purse
   for ship passage.
6. Enter the Three Bears' house while it is empty. Take the `just right`
   porridge for two points and the silver thimble for one. Outside, fill the
   thimble with flower dew for one.
7. Take dried mistletoe near the coast, wet mud from the stream with the spoon,
   and ocean water with the tin cup. Each is worth one point.
8. Visit the Oracle and receive the amber stone and Alexander's identity for
   three points. Find and take the eagle feather for two.
9. Complete the eagle transformation and use it to remove the giant spider
   guarding the cave. The two position branches converge on one four-point
   completion state; only one award is reachable.

These Llewdor collections and side quests contribute **48** points. Cumulative
score before spell completion: **87**.

## The Seven Spells

Each recipe must be performed in the laboratory with the wand temporarily
removed from its locked cabinet. Steps are ordered, and the empowering verse
must be recited exactly. A wrong ingredient, action, sequence, or verse enters
a failure branch instead of awarding ten points.

### Understand creatures

1. Put the chicken feather, dog fur, and snakeskin into the bowl.
2. Add a spoonful of powdered fish bone and the thimbleful of dew.
3. Mix with the hands, separate the dough into two pieces, and put them in
   Alexander's ears.
4. Recite:

```text
Feather of fowl and bone of fish,
Molded together in this dish,
Give me wisdom to understand
Creatures of air, sea and land
```

5. Wave the wand.

The dough remains in the ears and permits understanding animal speech. It is
useful for optional identity clues and for the pirate-hold treasure directions.

### Fly like an eagle or fly

1. Put saffron into the rose-petal essence.
2. Recite:

```text
Oh winged spirits, set me free
Of earthly bindings, just like thee.
In this essence, behold the might
To grant the precious gift of flight.
```

3. Wave the wand.

Dip the eagle feather or fly wings into the transformed essence to select a
temporary form. `Eagle begone! Myself, return!` and `Fly, begone! Myself,
return!` restore Alexander early. Use the fly form at the oak root hole and the
eagle form against the giant spider.

### Random teleportation

1. Grind the salt and mistletoe separately in the mortar.
2. Rub the Oracle's amber stone in the mixture, then kiss it.
3. Recite:

```text
With this kiss, I thee impart,
Power most dear to my heart.
Take me now from this place hither,
To another place far thither.
```

4. Wave the wand.

Rubbing the finished stone teleports Alexander to a random supported location.
It can shorten timed returns but is not a guarantee of safety.

### Deep sleep

1. Grind the acorns, put their powder in the bowl, add nightshade juice, and
   stir with the spoon.
2. Light the brazier, heat the mixture until most liquid is gone, remove it,
   spread it on the table, and wait for it to dry.
3. Recite:

```text
Acorn powder ground so fine
Nightshade juice, like bitter wine,
Silently in darkness you creep
To bring a soporific sleep
```

4. Wave the wand and put the powder in the purchased pouch.

On the pirate ship, pour the powder on the floor of the dank, dark hold and
recite `Slumber, henceforth!` to put the nearby crew to sleep.

### Transform another into a cat

1. Put mandrake-root powder, cat hair, and two spoonfuls of fish oil into the
   bowl. Stir the oily dough, put it on the table, shape it into a cookie, and
   let it harden.
2. Recite:

```text
Mandrake root and hair of cat
Mix oil of fish and give a pat
A feline from the one who eats
This appetizing magic treat
```

3. Wave the wand.

Put the finished cookie into the `just right` porridge before serving it to
Manannan.

### Brew a storm

1. Put the cup of ocean water in the bowl. Light the brazier and heat the bowl
   slowly without boiling, then remove it.
2. Add the spoonful of mud and toadstool powder, then blow into the brew.
3. Recite:

```text
Elements from the earth and sea,
Combine to set the heavens free.
When I stir this magic brew,
Great god Thor, I call on you.
```

4. Wave the wand and pour the brew into an empty jar.

To activate it outdoors, stir with a finger and recite `Brew of storms, Churn
it up!`. The corresponding early-stop phrase is `Brew of storms, Clear it
up!`.

### Become invisible

1. Cut the cactus with the knife, squeeze its juice onto the spoon, and put the
   juice into the bowl.
2. Add the lard and two drops of toad spittle, then stir.
3. Recite:

```text
Cactus plant and horny toad
I now start down a dangerous road
Combine with fire and mist to make
Me disappear without a trace
```

4. Wave the wand and return the ointment to the empty lard jar.

The single application works only where fire and mist coexist. Preserve it for
the dragon's cloud land.

Completing all seven preparations contributes **70** points. Cumulative score:
**157**.

### Freeing Alexander

1. Put the cat cookie into the porridge.
2. During Manannan's next hungry return, place the poisoned porridge before
   him. Do not offer another food first.
3. Manannan eats it without detecting the substitution and becomes a cat
   permanently. The completed transformation awards 12 points.
4. Retrieve all hidden possessions and the safely replaced wand as needed.
   Manannan no longer controls the house or its timers.

Cumulative score after liberation: **169**.

### Pirate voyage and treasure

1. Finish every Llewdor score event and store purchase before arranging
   passage. In the tavern show or give the remaining purse to the drunken
   captain. He takes it and awards three points.
2. Reach the dock before departure and board the ship for two points. The crew
   confiscates Alexander's possessions and locks him in the cargo hold.
3. With the animal-language dough still in place, listen to the mice. Their
   useful account locates buried treasure five paces east of a lone palm on the
   destination beach.
4. Cast the prepared sleep powder in the dark hold. Climb the crates and rope
   ladder to escape for two points while the crew sleeps.
5. Enter the captain's cabin, open his chest, and recover all confiscated
   possessions for three points. Take the shovel beside the lifeboat for one.
6. Wait until the ship anchors near land, leave it, and reach the beach. First
   arrival awards five points.
7. From the lone palm, move five paces east and dig with the shovel. Recovering
   the pirates' treasure chest awards seven points.

The passage, ship, arrival, and treasure chain contributes **23** points.
Cumulative score: **192**.

### Mountains, dragon, and home

1. Follow the cliff and cave route through the mountain range. Avoid falls,
   preserve both transformation components in the wind, and evade the
   Abominable Snowman. Completing the evasion awards four points.
2. Descend into ruined Daventry and speak to the old gnome if desired. His
   messages confirm Alexander's identity and Rosella's imminent sacrifice.
3. Reach the dragon's cloud land. Use the invisibility ointment where the
   dragon's fire and surrounding cloud mist satisfy its activation condition.
4. While unseen, activate the storm brew. Lightning kills the three-headed
   dragon and awards seven points.
5. Approach Rosella only after the dragon is dead and untie her for three
   points. Lead her down to the castle.
6. Enter the castle hallway with Rosella. This awards four points and starts
   the terminal family-reunion sequence.

The mountain contributes **4** and the dragon/rescue/return contributes **14**.
Final score: **210**.

## Score Ledger

| Phase | Selected awards | Phase total | Cumulative |
|---|---|---:|---:|
| House tools | Fly wings 1; bedroom discoveries 12; hidden possessions 4; lever/laboratory 9; kitchen food/tools 7; laboratory jars 6 | 39 | 39 |
| Llewdor | Raw ingredients and locations 24; bandit/purse/store/tavern 16; Medusa 5; Oracle 3 | 48 | 87 |
| Seven spells | Seven independent successful preparations at 10 each | 70 | 157 |
| Manannan | Poisoned-porridge cat transformation | 12 | 169 |
| Pirate route | Passage/boarding 5; hold/cabin/shovel 6; beach/treasure 12 | 23 | 192 |
| Mountains | Snowman evasion | 4 | 196 |
| Daventry | Dragon 7; Rosella 3; castle entry 4 | 14 | **210** |

The raw positive-site equation independently gives the same result:
`215 - 4 - 1 = 210`, where four is the second spider-position branch and one
is the second dog-fur parser branch.

## Deaths and Maximum-Score Dead Ends

- Ignore a chore, miss a return deadline, disturb sleeping Manannan, or remain
  in a forbidden room when he appears.
- Let Manannan see contraband, spell ingredients, the open trapdoor, or the
  missing wand. Repeated punishment can become terminal.
- Perform any spell step out of sequence, use a wrong ingredient, recite an
  incorrect verse, or omit the wand.
- Consume or lose a unique ingredient before its recipe is complete.
- Look directly at Medusa or let her touch Alexander before using the mirror.
- Touch the giant web as a human or fly, throw away the eagle transformation,
  or approach the spider incorrectly.
- Wake or get caught by a bandit, lose the purse before all store purchases, or
  miss the ship after paying the captain.
- Board without the sleep powder, storm brew, invisibility ointment, or other
  required possessions; there is no ordinary return to Llewdor.
- Let the pirates catch Alexander repeatedly, fall from the mast, walk the
  plank, enter shark water at the wrong time, or fail to recover possessions.
- Dig randomly without the mice's coordinate, leave the shovel aboard, fall in
  the mountain labyrinth, or let the snowman catch Alexander.
- Expose Alexander to the dragon, activate the storm without invisibility, let
  the map burn in the dragon's heat, or untie Rosella while the dragon lives.
- Reach the castle without Rosella; its doors remain closed and the terminal
  reunion cannot begin.

## Next Validation Work

1. Turn the safe-state invariants into an exact chore, absence, sleep, and
   inspection schedule under the original interpreter.
2. Record parser input for every spell step and verify all seven ten-point
   awards, including representative wrong-step failures.
3. Resolve exact movement and timing for Medusa, the spider, bandits, ship,
   treasure coordinate, snowman, dragon, and Rosella.
4. Record score, inventory, room, and story checkpoints at 39, 87, 157, 169,
   192, 196, and 210.
5. Package the validated input stream, screenshots, and terminal assertions as
   a repeatable implementation-conformance playthrough.
