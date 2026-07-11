# Space Quest 2 Playthrough Analysis

This chapter records a game-specific, clean-room reconstruction of a maximum-
score winning playthrough for the local `SQ2` evidence set. It is intended to
become a repeatable conformance scenario, not part of the portable AGI engine
specification. The route was derived from canonical logic, vocabulary, object,
picture, and view resources without consulting an external walkthrough.

The result is currently a **static candidate route**. Logic control flow,
messages, parser vocabulary, inventory mutations, and score mutations support
the story and puzzle sequence. Exact movement keystrokes, moving-hazard timing,
and score checkpoints still require replay under the original interpreter.

## Evidence Method

The reusable playthrough index can be generated with:

```bash
AGI_GAME_DIR=games/SQ2 \
  python3 -B tools/logic_playthrough_index.py \
  --output build/playthrough/sq2/index.json
```

The index contains 118 readable logic resources, 2,472 parser conditions, 182
room transitions, 70 score mutations, and 40 inventory slots. Directory entry
141 points at `VOL.0:0x1ffff`, which does not contain a valid resource header;
the index records it as unreadable and continues with valid resources.

Logic 104 assigns **250** as the declared maximum score. All positive score
sites sum to 283. The excess consists of alternate parser branches and puzzle
solutions rather than 283 points available on one designed path.

A direct renderer sweep produced all 74 valid picture resources. The resulting
contact sheet corroborates the forest, swamp, cave, shuttle, asteroid corridor,
Vohaul machinery, ruptured tube, pod-bank, and escape-pod progression described
below. Picture-directory entry 147 points at `VOL.0:0x2ffff`, where no valid
resource header exists; like unreadable logic 141, it is preserved as directory
evidence rather than interpreted as game content. Pictures 140 through 146 are
title or interface imagery rather than additional traversable rooms.

## Story State Model

The winning route has three large phases:

1. Work aboard Xenon Orbital Station 4, then be abducted and sent to Labion.
2. Escape Labion and take a shuttle to Sludge Vohaul's asteroid.
3. Infiltrate the asteroid, stop the salesman-clone launch, escape its orbital
   destruction, and enter suspended animation.

The terminal winning state is reached in logic 93 after entering the escape
pod's sleep chamber. Its messages state that Vohaul and the clone plan were
defeated, display the closing title, and leave the player in suspended
animation. The conformance scenario must reach this state with score 250.

## Candidate Route

### Orbital station and abduction

1. While working outside XOS 4, answer the wristwatch call by pressing its `C`
   control. This optional response awards one point.
2. Step onto the airlock platform when ordered inside. Completing the transfer
   into the airlock awards one point.
3. Change from the EVA suit into the station uniform at the suit rack. This
   awards one point and retains the order form and dialect translator.
4. Open Roger's locker and take both the athletic supporter and Cubix Rube
   puzzle. Each is a separately guarded one-point acquisition.
5. Travel through station control to the shuttle bay and enter the shuttle.
   The abduction sequence awards five points and eventually deposits the
   captive player on Labion.

End-of-phase score: **10**.

### Labion forest and swamp

1. After the hovercraft crash, press the flashing, beeping button in the wreck
   to switch off its locator for one point. Search the dead guard and take the
   keycard for three points.
2. Find the small pink being caught in a snare and free it by releasing the
   rope. Its escape awards five points and establishes the later cliff-dweller
   welcome state.
3. In the spore clearing, take one live spore for four points. The two four-
   point sites are alternate near/far acquisition branches guarded by the same
   state, not cumulative awards.
4. Put the order form into the clearing's mailbox for two points. Return after
   its delivery cycle and take the whistle from the tray for another two.
5. Survive the root-monster area and take the red berries for two separate
   four-point awards: one for completing the encounter and one for acquiring
   the berries. Rub the berries over Roger's body for three points. Their odor
   is used to avoid detection by the searching hovercraft; completing that
   evasion awards five points.
6. At the swamp, take a deep breath before diving. The first valid breath/dive
   state awards two points. Reach the underwater grotto for two points, take
   another breath there for two, and take the glowing gem for three. This is
   the higher-valued gem acquisition; do not later take the one-point fallback
   gem in the cliff-dweller cave.
7. Allow the forest hunter sequence to capture Roger and place him in the cage.
   Throw the live spore at the hunter from the proper position to paralyze him
   for five points. Take the cage key for two, unlock and open the cage, then
   take the rope for two.
8. Return to the fissure. Climb the dead snag for three points, then tie the
   rope to either the stump or the log for two. The two anchor awards are
   alternatives; untying the rope removes two points.
9. Descend the fissure and swing on the rope. Initiating the useful swing
   awards two points. Release at the correct part of the arc to reach the
   ledge, awarding five points.
10. The cliff dwellers recognize the earlier rescue. Follow them through their
    cave and, when their leader offers to reveal the exit, `say the word`. This
    awards three points and opens the descending route.
11. In the dark tunnels, hold the glowing gem in Roger's mouth so he can crawl
    while retaining light. Successfully reaching the luminous underground
    water awards 20 points.
12. Follow the river and survive the forced whirlpool sequence. Reaching the
    waterfall pool outside awards five points.
13. In the terror-beast clearing, blow the mail-order whistle to summon the
    beast for five points. Give it the Cubix Rube for ten; while it is occupied
    by the puzzle, take the small stone from the newly created debris for two.
    The two stone pickup sites describe the same inventory acquisition.
14. At the landing platform, use the athletic supporter as a sling and fire the
    stone at the guard while outside his direct line of sight. The successful
    hit awards 20 points. The two ten-point bush-distraction branches are
    lower-valued alternatives and consume the same stone.
15. Search the unconscious guard and take his keycard for one point. Insert it
    into the elevator slot for five.
16. In the shuttle, power the ascent system, select vertical attitude control,
    activate the ascent thrusters, and use the throttle as indicated by the
    console. Achieving the required altitude and departure sequence awards 20
    points. Vohaul then takes remote control and brings the shuttle to his
    asteroid.

Labion contributes **156** points. Cumulative score: **166**.

### Vohaul's asteroid

1. Explore the asteroid's elevator levels before committing to the final
   security route. Collect the following janitorial and utility items:

   - Plunger from the dark closet in room 62: one point.
   - Glass cutter from the dark closet in room 72: one point.
   - Toilet paper from the human restroom in room 76: one point.
   - Wastebasket and lighter from the holding-level closet in room 83: one
     point each. Inspecting or taking the dirty overalls exposes the lighter.

2. Put the toilet paper into the wastebasket for one point. Preserve the
   resulting basket-with-paper for the Wallbot corridor.
3. Enter the moving-floor acid trap in room 66. Completing its first barrier
   sequence awards ten points. At the smooth barrier, attach the plunger and
   hang from it while the floor retracts; the successful plunger state awards
   another ten. Do not release early.
4. In the Wallbot corridor, put down the loaded wastebasket in the accepted
   position for one point and ignite it with the lighter. The heat triggers the
   sprinklers; the water extinguishes the fire and shorts the Wallbots. The
   successful sequence awards ten points.
5. Enter Vohaul's control chamber. The miniaturization beam traps Roger in a
   glass jar on the console. Use the glass cutter to cut an exit and complete
   the miniature escape sequence for five points.
6. Enter the console vent, reach Vohaul's life-support machinery, and press the
   emergency shutoff. Disconnecting his life support awards ten points. Return
   to the console and use the beam sequence to regain normal size.
7. Examine Vohaul's hand to learn the written code `SHSR`. Use the control
   console and enter `SHSR` to abort the salesman-clone launch for ten points.
   This action starts the asteroid's terminal orbital-decay phase.
8. Open the wall receptacle in the clear outer passage and take the oxygen mask
   for two points. Wear it before traversing any ruptured, depressurized tube.
9. Return to the escape-pod bank while avoiding the Marrow-Matic and other
   moving hazards. Enter the available pod for ten points and launch before the
   asteroid is destroyed.
10. After launch, the pod reports rapidly dwindling oxygen. Open the sleep
    chamber and enter it. Sealing the chamber awards the final ten points and
    enters terminal logic 93.

The asteroid contributes **84** points. Final score: **250**.

## Score Ledger

| Phase | Selected awards | Phase total | Cumulative |
|---|---|---:|---:|
| XOS 4 and abduction | 1, 1, 1, 1, 1, 5 | 10 | 10 |
| Labion | 3, 1, 3, 5, 2, 3, 2, 5, 2, 2, 4, 2, 2, 4, 4, 2, 5, 2, 2, 2, 3, 3, 20, 5, 2, 5, 10, 1, 20, 5, 20, 5 | 156 | 166 |
| Vohaul's asteroid | 1, 10, 1, 10, 10, 1, 1, 1, 1, 10, 5, 10, 2, 10, 10, 1 | 84 | 250 |

The complete positive-site sum is 283. The designed route removes 33 points:

| Excluded alternatives | Excess removed |
|---|---:|
| Duplicate airlock supporter/puzzle parser branches | 4 |
| Duplicate spore acquisition | 4 |
| Second rope anchor | 2 |
| One-point fallback glowing gem | 1 |
| Duplicate terror-beast stone acquisition | 2 |
| Two ten-point guard distraction alternatives instead of the 20-point hit | 20 |
| **Total** | **33** |

Thus `283 - 33 = 250`. No negative score action is needed. Avoid changing
back into the EVA suit, untying the rope after scoring an anchor, and trying to
retrieve the suspended wastebasket from an invalid position.

## Deaths and Dead Ends

The logic resources expose many useful negative conformance cases:

- Step off the orbital-station structure and drift into space.
- Leave the airlock without the EVA suit.
- Enter concealed forest spike pits or touch sticky/insect-covered trees.
- Approach the root monster incorrectly or fail to escape its digestive path.
- Enter deep swamp water without taking a breath or remain submerged too long.
- Let the hunter recover before escaping the cage.
- Fall from the fissure, mistime the rope release, or enter dark caves without
  the gem.
- Meet the cliff dwellers without having rescued their companion.
- Enter the cave-squid tunnel without enough light or take the fatal river
  branch.
- Approach the terror beast without distracting it.
- Let the platform guard see Roger while attacking or following him.
- Fall from asteroid walkways or enter vacuum without the oxygen mask.
- Release the plunger during the acid-floor trap.
- Approach active Wallbots, Marrow-Matics, floor waxers, or caged creatures.
- Fail to stop the clone launch or remain on the asteroid during orbital decay.
- Set the miniaturization beam incorrectly, remain trapped without air, or fail
  to disable Vohaul's life support.
- Launch successfully but fail to enter suspended animation before the pod's
  oxygen is exhausted.

Potential progression dead ends include discarding the puzzle, supporter,
whistle, gem, keycards, plunger, glass cutter, lighter, paper, or wastebasket
before its final use. A conformance suite should distinguish these valid but
unwinnable states from immediate death states.

## Next Validation Work

1. Convert each milestone into exact movement and parser input under QEMU.
2. Record room, inventory, and score checkpoints at 10, 166, and 250.
3. Confirm moving-hazard timing, patrol evasion, rope release, acid-floor
   survival, and Wallbot placement under the original interpreter.
4. Package the validated input stream, screenshots, and terminal assertions as
   a repeatable implementation-conformance playthrough.
