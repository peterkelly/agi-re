# King's Quest 1 Playthrough Analysis

This chapter records a game-specific, clean-room reconstruction of a maximum-
score winning playthrough for the local `KQ1` evidence set. It is intended to
become a repeatable conformance scenario, not part of the portable AGI engine
specification. The route was derived from canonical logic, vocabulary, object,
picture, and view resources without consulting an external walkthrough.

The result is currently a **static candidate route**. Logic control flow,
messages, parser vocabulary, inventory mutations, score mutations, and room
transitions support the complete puzzle sequence. Exact movement coordinates,
random-character timing, and the final input stream still require replay under
the original interpreter.

## Evidence Method

The reusable playthrough index can be generated with:

```bash
AGI_GAME_DIR=games/KQ1 \
  python3 -B tools/logic_playthrough_index.py \
  --output build/playthrough/kq1/index.json
```

The index contains 90 readable logic resources, 1,478 parser conditions, 277
room transitions, 180 score mutations, and 27 inventory slots. No logic
resource failed to decode. Logic 0 assigns **158** as the declared maximum
score. The 269-point raw positive-site sum includes repeated room variants,
reversible acquisitions, lower-valued alternatives, and positive halves of
net score exchanges; it is not a reachable route total.

A direct renderer sweep produced all 82 present picture resources without an
error. The resulting contact sheet corroborates the open Daventry map, well
and dragon caves, condor flight, underground leprechaun complex, beanstalk and
cloud region, giant territory, castle return, and ending imagery. Pictures 83
and 84 are title or transition imagery rather than traversable rooms.

## Winning State

King Edward sends Graham to recover three objects:

1. A magic mirror that tells the future.
2. A magic shield that protects its bearer.
3. A magic chest that continually supplies gold coins.

Logic 53 recognizes the completed quest when all three treasure states are
present. After Graham returns to the throne room and bows, King Edward rises,
commends him, dies, and grants him the kingdom. The terminal sequence names
Graham as King of Daventry and displays the closing credits. The conformance
scenario must reach that sequence with score 158.

## Maximum-Score Principles

Several parser choices solve the same immediate problem but do not preserve
the maximum score:

- **Show**, rather than give, the carrot to the goat. Showing it awards five
  points while retaining the two-point carrot. Giving or feeding it first
  subtracts those two points.
- Use water on the dragon. Consuming the two-point water and receiving the
  seven-point solution award gives a net five, compared with the lower-valued
  dagger solution.
- Give food rather than treasure to gatekeepers. Cheese costs two points but
  earns four from the rat; surrendering a six-point treasure only removes it.
- Drive the leprechauns away with fiddle music and retain the four-leaf clover
  as protection.
- Wait for the giant to fall asleep. This earns seven points and leaves the
  eight-point chest available. Killing him with the sling gives a lower net
  result.
- Answer the gnome correctly on the first guess. Later correct guesses award
  fewer points, while failure produces a gold key and a lower-valued alternate
  route instead of the beans.

The parser's first-guess word for the gnome is `ifnkovhgroghprm`. The witch's
note says that it can be wise to think backwards. Mechanically mirroring each
alphabet position (`a` with `z`, `b` with `y`, and so on) transforms that local
vocabulary token into `rumplestiltskin`.

## Candidate Route

The surface world is open enough that many collection steps can be reordered.
The sequence below keeps dependencies explicit and avoids carrying the goat
into rooms where it wanders away or causes a score penalty.

### First audience and surface preparations

1. Cross the castle bridge, open the door, enter the throne room, stand a few
   paces in front of King Edward, and bow. Opening the door awards one point;
   the first respectful bow awards three. Speak to the King to receive the
   three-treasure quest.
2. Move the large rock in the birch clearing for two points. Search the exposed
   hole and take the dagger for five. Stand uphill or aside so the moving rock
   does not roll over Graham.
3. Look inside the decaying stump for one point, take the canvas pouch for
   three, and open it for another three. It becomes the pouch of diamonds.
4. Take a carrot for two points. At the goat pen, open the gate and **show the
   carrot** from close range. This awards five points without consuming it and
   causes the goat to follow Graham.
5. Lead the goat to one of the guarded bridges. Step aside when the troll
   appears. The goat butts the troll away for four points and then leaves the
   active route. Do not pay the troll with treasure.
6. Speak to the nearby elf from close range. The successful encounter awards
   three points and leaves Graham with the magic ring. The maximum route does
   not need to activate the ring; dropping or losing it can subtract points.
7. Take the four-leaf clover for two points. It later suppresses hostile
   leprechaun behavior.
8. Take one walnut from the walnut tree for three points, then open it to reveal
   that its interior is gold for another three.
9. Take the ceramic bowl for three points. Read its underside for one, say
   `fill` to obtain stew for two, and give the full bowl to the starving
   woodcutter family. Giving the three-point bowl and receiving the six-point
   generosity award is a net three. Take their offered fiddle for three.
10. Take the smooth pebbles at the river delta for one point. They are not used
    against the giant on the maximum route, but their acquisition still scores.

### Witch, gnome, and condor

1. At the gingerbread house, eat part of the exterior for two points. Enter
   only when the witch is away or position Graham so she cannot catch him.
2. When the witch turns to tend the oven, push her into it from close range for
   seven points. Open the cabinet for two, take the cheese for two, and take the
   note for two. Read the note for one additional point.
3. Visit the gnome and accept the three-guess challenge. Enter
   `ifnkovhgroghprm` as the first guess for five points, then take the magic
   beans for four.
4. Plant the beans in one of the fertile-soil rooms for two points. The
   resulting beanstalk remains available for the chest route.
5. In the condor clearing, time a jump so Graham intersects the low-flying
   bird. Being carried away awards three points. The condor flight passes
   through room 80 and deposits Graham in room 48.
6. Before entering the underground route, visit the neighboring far riverbank
   and take the mushroom for one point. Return to room 48 and use its opening
   to fall into room 73.

Surface preparation, including the first audience, contributes **83** points:
four for the audience and 79 for the surface puzzles and acquisitions.

### Magic mirror

1. At the well, use its bucket and rope to descend. Cut the bucket rope with
   the dagger from the valid in-water position. The route awards two points for
   acquiring the bucket and two for its first fill, either during this action
   or at the next valid water source.
2. Entering the well shaft from room 12 awards one point. Dive from the valid
   swimming state for two and reach the bottom chamber.
3. Enter the side opening into the dragon cave for one point. From the safe
   side of the cave, throw the bucket's water at the dragon. Consuming the water
   subtracts two points and the nonviolent solution awards seven, for a net
   five.
4. Take the magic mirror for eight points. Return through the opening to the
   bottom chamber once for two points, then use the passage exposed when the
   dragon moved the boulder to leave the cave system.

The mirror chain contributes **23** points. Cumulative score: **106**.

### Magic shield

1. Follow rooms 73 and 74 to the rat's door in room 75. Give the cheese from
   close range. Losing its two acquisition points and receiving four for the
   intended solution gives a net two; the rat opens the way.
2. Enter the leprechaun antechamber with the four-leaf clover in inventory.
   Play the fiddle for three points. The leprechauns dance away and their King
   follows them out.
3. In the throne room, take the magic shield for eight points and the sceptre
   for six.
4. Continue to room 78. Eat the mushroom there: its one-point consumption and
   three-point room-specific award give a net two. Pass through the tiny exit
   to room 36 for one additional point and return to normal size after the
   mushroom's timer expires.

Including the earlier one-point mushroom acquisition, the shield chain
contributes **23** points. Cumulative score: **129**.

### Magic chest

1. Return to the planted beanstalk and climb it carefully into the clouds.
   Reaching the bird-nest region for the first time awards two points.
2. Search the hollow cloud-tree and take the leather sling for two points. Take
   the golden egg from the nest for six.
3. Approach the giant's region without attacking. Evade him until his patience
   state expires and he falls asleep; this awards seven points.
4. Take the magic chest from the sleeping giant for eight points. Do not use
   the sling and pebble against him: that consumes a point and replaces the
   seven-point sleep outcome with a three-point kill outcome.
5. Return across the cloud paths and descend the beanstalk without falling.

The chest chain contributes **25** points. Cumulative score: **154**.

### Return to King Edward

1. Return to the castle after all three treasure states are complete. Opening
   its door on the completed-quest return awards the second one-point door
   event.
2. Stand in the audience rectangle and bow again. The completion-state bow
   awards three points and starts the terminal commendation sequence.

Final score: **158**.

## Score Ledger

| Phase | Selected net awards | Phase total | Cumulative |
|---|---|---:|---:|
| First audience | Door 1; bow 3 | 4 | 4 |
| Surface preparations | Rock/dagger 7; pouch 7; carrot/goat/troll 11; elf 3; clover 2; walnut 6; bowl/family/fiddle 12; pebbles 1; gnome/beans 11; witch 16; condor 3 | 79 | 83 |
| Magic mirror | Bucket/water 4; well entry 1; dive 2; cave entry 1; water solution net 5; mirror 8; cave return 2 | 23 | 106 |
| Magic shield | Mushroom acquisition/consumption/exit 4; rat solution net 2; fiddle 3; shield 8; sceptre 6 | 23 | 129 |
| Magic chest | Cloud entry 2; sling 2; egg 6; sleeping giant 7; chest 8 | 25 | 154 |
| Final audience | Door 1; bow 3 | 4 | **158** |

The route contains four deliberate negative score mutations, each paired with
a larger positive award:

| Consumed state | Deduction | Solution award | Net |
|---|---:|---:|---:|
| Full bowl given to the woodcutters | -3 | +6 | +3 |
| Water thrown at the dragon | -2 | +7 | +5 |
| Cheese given to the rat | -2 | +4 | +2 |
| Mushroom eaten in room 78 | -1 | +3 | +2 |

Showing the carrot incurs no deduction. The `give/feed carrot` parser branches
would add an unnecessary two-point loss and make 158 unreachable on that run.

## Deaths and Maximum-Score Dead Ends

The logic resources expose useful negative conformance cases:

- Fall into the castle moat or enter swift/deep water without the correct
  swimming state.
- Stand downhill from the moved rock and be crushed.
- Let wolves, the sorcerer, ogres, dwarfs, the witch, the rat, trolls, or
  leprechauns catch Graham without the relevant protection or solution.
- Enter the witch's house at the wrong time and be caged or cooked.
- Fall while climbing the well rope, beanstalk, cloud paths, or tree.
- Remain underwater too long at the well bottom.
- Approach the dragon through its flame path or remain in range after the
  shield melts.
- Miss the condor jump or fall from its transport sequence.
- Eat the mushroom in a place where Graham becomes trapped when normal size
  returns.
- Approach the awake giant or walk off the clouds.

Valid but lower-scoring branches include feeding the carrot, giving treasure
to the troll or rat, killing the dragon with the dagger, killing the giant with
the sling, guessing the gnome's name late, failing the gnome puzzle and taking
the key route, or losing inventory to the roaming dwarf. Dropping the quest
treasures can also create a terminally unwinnable state. These should be tested
separately from immediate death behavior.

## Next Validation Work

1. Convert each milestone into exact movement, parser input, and jump timing
   under QEMU.
2. Record room, inventory, treasure-count, and score checkpoints at 4, 83, 106,
   129, 154, and 158.
3. Confirm timing-dependent condor, witch, dwarf, giant, cloud, well, and
   beanstalk behavior under the original interpreter.
4. Package the validated input stream, screenshots, and terminal assertions as
   a repeatable implementation-conformance playthrough.
