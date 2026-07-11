# Space Quest 1 2.2 Playthrough Analysis

This chapter records a game-specific, clean-room reconstruction of a winning
playthrough for the local `SQ1.22` evidence set. It is intended to become a
repeatable conformance scenario, not an AGI engine specification. The route is
derived from the canonical directory and volume resources, `WORDS.TOK`, and
`OBJECT`. It does not use an external walkthrough.

The current result is a **static candidate route**. The story dependencies and
most puzzle actions are well supported by logic control flow and messages. The
exact movement keystrokes, timing-sensitive encounters, gambling sequence, and
possible over-maximum guard award still require an original-interpreter replay.
Static control flow now supplies a complete designed 202-point ledger.

## Evidence Method

`tools/logic_playthrough_index.py` produces a machine-readable index containing
decoded messages, parser word groups, room changes, inventory mutations, and
score mutations. Run it with:

```bash
AGI_GAME_DIR=games/SQ1.22 \
  python3 -B tools/logic_playthrough_index.py \
  --output build/playthrough/sq122/index.json
```

The game uses interpreter version 2.917. Its canonical resources contain 101
logic scripts, 73 pictures, 238 views, and 50 sounds. Logic 104 assigns 202 to
the maximum-score variable. The sum of all positive score sites is greater than
202 because the bytecode contains mutually exclusive purchases and traversal
branches, as well as point reversals and penalties.

The files `LOGIC.000`, `logic0.txt`, and `SQSG.1` found beside the canonical
resources were not treated as authoritative route evidence.

## Story State Model

The winning path has four large phases:

1. Escape the Arcada with the Star Generator cartridge.
2. Survive Kerona, help its inhabitants, and obtain transport.
3. Learn the Deltaur's location and buy a ship and flight droid at Ulence
   Flats.
4. Infiltrate the Deltaur, destroy the Star Generator, and escape.

The terminal winning state is logic 64. Its messages congratulate the player,
award a golden mop, and advertise the sequel. Logic 63 immediately precedes it
and states that the Deltaur has been destroyed. Reaching this state is not by
itself sufficient for the proposed test: the score must also equal the declared
maximum of 202.

## Candidate Route

### Arcada and escape pod

1. In the archive, remain for the dying scientist's complete warning. His last
   useful phrase identifies the cartridge title as `astral body`.
2. Use the archive terminal/retrieval unit to find that title, then `get
   cartridge`.
3. Search the dead crew member in room 3 and `get keycard`.
4. Reach the bay-door controls in room 6 and open the bay door. Do not close it
   again: the reverse operation removes the points awarded for opening it.
5. At the elevator in room 7, insert or use the keycard in the slot.
6. In Flight Prep, use the closet controls, take both the flight suit and the
   gadget, and wear the flight suit.
7. In the vehicle bay, press the platform control once and enter the escape
   pod.
8. Close the pod door, fasten the seat belt, turn on power, press AutoNav, and
   pull the throttle. The bay must already be open.
9. After landing on Kerona, unfasten the belt, take the survival kit, and leave
   the pod.

Static control flow supports all of these dependencies. The precise archive
terminal interaction is still to be transcribed into keystrokes for automation.

### Kerona surface and caverns

1. At the wrecked pod in room 30, take the reflective glass.
2. Open or inspect the survival kit. The global inventory logic replaces it
   with dehydrated water and a Xenon army knife.
3. Visit the rock arch in room 17. Its first completed approach awards points.
4. Pass through the arch and its connector to room 25. Take the nearby rock
   **before** entering room 26. Taking it in room 25 has no score deduction;
   taking it after it is present in room 26 subtracts four points.
5. In room 26, put the rock in the steam geyser. This awards four points and
   changes the traversable geometry.
6. Cross room 27's upper acid-pool path without entering or drinking from the
   pool. The successful traversal awards three points.
7. In room 28, use or hold the reflective glass in the energy beams. Reflecting
   the beam into its emitter disables the barrier and awards five points.
8. Meet the Keronian projection in room 29. It tasks the player with killing
   Orat and returns the player to the surface.
9. In room 19, push the large boulder from the required side. The resulting
   object sequence destroys the spider droid and awards five points.
10. Enter Orat's cave in room 24. Give or throw the dehydrated-water container
    to Orat. The water solution awards five points and kills Orat. Take the
    Orat part for two points.
11. Return through the arch and underground rooms to room 29, then drop the
    Orat part. This awards ten points and reveals the way into room 31.
12. In room 31, insert the Star Generator cartridge into the console and read
    it. It identifies the self-destruct code as `6858`. Remove the cartridge
    again. Insertion and retrieval are separately guarded five-point events.
13. Board the sand skimmer and turn its key. Its fixed journey leads through a
    boulder-field sequence to Ulence Flats.

The spider droid and Orat also have a combined ten-point cave-resolution path.
It shares a one-time award flag with the five-point boulder event. The combined
path is therefore an alternative to the five-point boulder plus five-point
water route above, not an additional ten points.

The surface room graph is interconnected and permits several orders. The route
above orders prerequisites rather than claiming a shortest movement path.

### Ulence Flats

1. On first arrival, the skimmer sequence awards 25 points.
2. Accept the final sale offer for the skimmer. The branch that also supplies a
   jetpack awards five points; retaining the jetpack is required later.
3. Find the five buckazoids behind the building in room 38.
4. In the bar, buy and drink three beers. The third drink reveals that the
   Deltaur is in sector `HH` and awards five points. Further drinking produces
   intoxication without another route requirement.
5. Use the slot machine to obtain enough money for the flight droid and the
   214-buckazoid cruiser. The machine accepts one-, two-, or three-buckazoid
   bets and has outcomes including loss, payouts, and death. This is the main
   unresolved deterministic-automation problem: a replay can save before each
   wager, prescribe a known input/timing sequence, or restore on losing runs.
6. In Droids-B-Us, buy the 45-buckazoid flight-systems droid. It is the droid
   described as able to pilot a fighter or cruiser. The purchase awards four
   points. A coupon branch reduces the price to 36; coupon acquisition is not
   yet part of the static route.
7. At Tiny's lot, buy the 214-buckazoid Drallion cruiser. The purchase awards
   four points. A separate 144-buckazoid branch exists only after obtaining a
   70-buckazoid credit and is mutually exclusive with the direct purchase.
8. Enter the cruiser, press `LOAD` to load the flight droid, and answer `HH`
   when asked for a sector.

Buying a cheaper non-flight droid is a dead end: the selected cruiser has no
manual controls and requires a suitable droid.

### Deltaur infiltration

1. Keep the jetpack on when leaving the cruiser. Approach the Deltaur airlock,
   turn its handle, and enter. Removing the jetpack in open space is fatal.
2. Allow the maintenance droid to cycle the inner airlock. Entering the ship
   awards one point.
3. Reach the laundry room. Open the cleaning unit, climb into it, and survive
   the cycle to emerge in a Sarien uniform. This disguise transformation awards
   five points.
4. Use the trunk and ventilation system where required. The room-57 sequence
   is explicit in its own hint: push the trunk to the wall, climb the trunk,
   open the vent, and enter it. The Xenon army knife opens the accessible
   grate. Store or relinquish the jetpack as required before entering a narrow
   vent. A successful trunk transition awards three points; one of two
   alternative vent-entry branches awards two points.
5. Search a dead Sarien for its ID card. The card identifies its owner as
   Butston Freem.
6. While the disguise permits conversation, talk to a Sarien guard once and
   attempt to kiss one once for one point each. When a guard asks whether the
   player owns King's Quest II, answer `yes` for five points. These deliberately
   comic interactions are part of the 202-point ledger even though they are not
   progression prerequisites.
7. While disguised, visit the armory in room 51. Present the Sarien ID card to
   obtain a pulseray for three points. Two gas grenades can each be taken for
   one point while the droid is not observing the theft; being caught leaving
   with one is fatal.
8. Avoid the optional three-point roaming-guard defeat. Neutralize the guard in
   room 50 with the five-point pulseray/projectile path and avoid contact with
   the guardian droid. The designed score ledger includes the room-50 award,
   not the lower-value roaming award. Static logic does not yet prove that
   collecting the roaming award first makes the later award unreachable; this
   is the possible 205/202 overscore case to test dynamically.
9. In the Star Generator chamber, search the fallen guard and take the remote
   control for three points. From a safe distance, press its button to disable
   the generator's force field for three more. Reactivating it while close is
   fatal.
10. At the generator panel, enter the cartridge's `6858` self-destruct code.
   Completing the sequence awards ten points and starts a five-minute timer.
11. Reach the launch bay in room 62, enter the one-person shuttle, and press
    `launch`. First entry and launch award one and three points respectively.
12. The successful escape enters logic 63 and then terminal winning logic 64.

The precise corridor route through rooms 48-62 and the timing of moving guards
remain to be turned into directional input. The room graph and required
interaction states are known.

## Score Ledger

The bytecode contains the following selected awards. A parenthesized pair means
the sites are known alternatives, not cumulative awards.

| Phase | Selected awards | Route total |
|---|---|---:|
| Arcada and landing | 5, 2, 1, 2, 2, 1, 2, 2, 2, 15, 25, 2 | 61 |
| Kerona | 2, 5, 2, 5, 4, 3, 5, 10, 3, 5, 5 | 49 |
| Ulence Flats | 25, 5, (4 or 4), 5, 4 | 43 |
| Deltaur | 3, 3, 1, 1, 3, 1, 5, 1, 1, 3, 10, 5, 3, (2 or 2), 5, 1, 1 | 49 |
| **Total** | | **202** |

The corresponding end-of-phase score checkpoints are 61 after the Kerona
landing setup, 110 after departing Kerona, 153 after leaving Ulence Flats, and
202 at the terminal victory. These are suitable first-pass replay assertions.

The complete positive-site sum is 221. The designed ledger removes four points
for the duplicate ship-purchase branch, two for the duplicate vent-entry
branch, ten for mutually exclusive Orat/spider solutions, and three for the
lower-valued roaming-guard defeat: `221 - 4 - 2 - 10 - 3 = 202`.

No deduction is required on this route. Take the rock in room 25, do not kick
bodies, do not reverse the bay/platform state, do not collide with the guardian
droid, and do not try to enter a closed vent. The original-interpreter replay
must test whether the optional three-point roaming-guard award can coexist with
the selected room-50 award. If it can, 205 may be reachable despite the game
declaring 202 as its maximum; the test objective must then distinguish the
declared maximum from the greatest mechanically reachable score.

## Deaths and Dead Ends

The route analysis already exposes representative failure classes suitable for
negative conformance scenarios:

- Entering an unknown cliff hole makes the player a creature's lunch.
- Drinking or entering the acid pool is fatal.
- Approaching Orat without the water solution is fatal.
- Being detected by the spider droid causes molecular destruction.
- Standing in the desert too long risks Grell.
- Crashing the skimmer or buying/flying unsuitable transport is fatal or a
  progression dead end.
- Losing all money at the slot machine prevents required purchases; one reel
  outcome is explicitly labeled death.
- Leaving the approach craft without the jetpack is fatal.
- Losing the helmet before the disguise is secure exposes the player.
- Firing in the armory, stealing in view of its droid, or presenting invalid
  credentials is fatal.
- Contact with the guardian droid, loitering near armed Sariens, or missing a
  shot is fatal.
- Reactivating the Star Generator force field while nearby vaporizes the
  player.
- Failing to reach and launch the shuttle before self-destruction expires
  prevents the winning transition.

## Next Validation Work

1. Build a stateful score-path model from the condition tree rather than the
   current enclosing-range index.
2. Render and label the Arcada, Ulence Flats, and Deltaur room pictures to map
   directional transitions to visible landmarks.
3. Run the candidate route under the original interpreter, recording room,
   inventory, and score checkpoints after each milestone.
4. Resolve slot-machine determinism and generate a repeatable money sequence.
5. Convert the validated route into a QEMU input script with checkpoints and
   expected screenshots, score values, and terminal state.
