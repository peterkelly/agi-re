# Gold Rush Playthrough Analysis

This chapter records a game-specific, clean-room reconstruction of a maximum-
score winning playthrough for the local `GR` evidence set. It is intended to
become a repeatable conformance scenario, not part of the portable AGI engine
specification. The route was derived from the game's logic, messages,
vocabulary, objects, pictures, and views. No external walkthrough or AGI
documentation was consulted.

The result is currently a **static candidate route**. Script control flow,
parser vocabulary, inventory transformations, score mutations, route
checkpoints, and ending messages support a complete 255-point route. Exact
movement, timed departures, random hazards, and the final input stream still
require replay under the original interpreter.

## Evidence Method

The reusable playthrough index can be generated with:

```bash
AGI_GAME_DIR=games/GR \
  python3 -B tools/logic_playthrough_index.py \
  --output build/playthrough/gr/index.json
```

The full game uses interpreter 3.002.149 and the v3 combined directory and
prefixed-volume container. The index contains 182 readable logic resources,
6,227 parser conditions, 431 room transitions, 150 immediate score mutations,
and 131 inventory slots. No present logic failed to decode.

Logic 101 initially assigns 250 as the displayed maximum. Buying the Panama
ticket in logic 3 assigns route value 2, awards nine points, and raises the
maximum to **255**. This is not the Cape Horn branch: route 2 requires mosquito
netting, invokes the Panamanian-jungle controller, and is checked against a
100-point arrival total. Route 1 requires citrus fruit, follows Cape Horn, and
has a 95-point arrival total. The overland route uses route value 3.

All 186 present picture resources decode in a qualitative brush-disabled
sweep. That sheet predates the cross-interpreter brush audit, so it
corroborates geography and interiors but is not pixel-conformance evidence.
The later audit maps GR's mask table at `0x1430`, pointer table at `0x1450`,
radius-one center-row shape, and v3 horizontal clamp.

## Story and Winning State

Jerrod Wilson lives in Brooklyn and works for a newspaper. A letter from his
long-lost brother Jake contains a gold flake and a request to come to the area
drained by the American River. In California, Jake is using the name James and
has concealed a trail of family clues to keep his discovery secret.

Jerrod can travel by Cape Horn, Panama, or the overland trail. The highest
declared terminal score requires Panama. After crossing the isthmus, he reaches
Sacramento and Sutter's Fort, recovers the trail to James, follows James' mule
to a cabin, and enters the mine beneath it. Logic 162 reunites the brothers.
Logic 193 then reveals the exceptionally pure gold vein, awards the final six
points for non-overland routes, displays the success messages, and reaches the
terminal thank-you state at score 255.

## Global Constraints

1. Sell the Brooklyn house before the gold-rush state lowers its value. The
   early sale awards nine points; the late sale awards only six.
2. Use the Panama ship ticket and buy mosquito netting. Citrus fruit belongs
   to Cape Horn, while the ferry and stage ticket out of New York belong to the
   overland route.
3. Stay off the Brooklyn park grass. Repeated violations subtract up to three
   points and prevent the exact 60-point departure checkpoint.
4. Cooperate when the armed Panamanian group demands valuables. Refusal is
   fatal. The robbery intentionally advances the route while preserving the
   family evidence needed later.
5. Keep moving through the jungle, retain the mosquito net, use the vine when
   ants cover the trail, and avoid snakes, alligators, swamp, and disease
   delays.
6. Keep the ancient gold disk. Spending it on a mule or shovel subtracts two
   points and removes a unique object. Ordinary California gold can fund the
   mule; the Brooklyn gold coin can buy the shovel.
7. Brand Jerrod's mule before stabling it. Select the same branded mule when
   retrieving it; choosing an unbranded or differently branded animal leads to
   rejection or execution for theft.
8. Preserve the note, magnet, string, matches, lantern, steel key, and pick.
   They form the cabin and mine dependency chain.
9. Gold accumulation is score-bearing. Logic 110 awards one point for each
   successful increase in the gold-amount state, up to 50 outside the deep
   mine and 70 in mine rooms 147--163. The maximum route must reach the shared
   70-award cap without triggering the robbery penalty.
10. The score is byte-sized. Avoid penalties and unintended extra/alternate
    branches so the final six-point award lands on 255 rather than wrapping.

## Candidate Route

### Brooklyn: 60 points

1. At home, inspect the family album and take the family photograph. Retrieve
   the bank statement from the roll-top desk, read it, and retain the account
   number.
2. Obtain Jake's letter from the post office. Open and read it, inspect its
   postmark, then lift the stamp to expose the hidden gold flake.
3. In the parks, take the gold coin and pick the flowers without walking on
   the grass. At the cemetery, read both Wilson family stones and place the
   flowers on the family graves.
4. Read the travel sign. At the newspaper office, examine the California
   clipping and formally quit while speaking to the boss at close range.
5. Sell the house while property values are still at their premium. This must
   precede the state change that reduces the award from nine to six.
6. At the bank, use the statement's account number and complete the withdrawal
   sequence. Do not lose the statement before reading it.
7. At 12 Front Street, choose **Panama** and buy the ticket. Buy mosquito
   netting from the hardware store. Both the purchase path and the dock check
   share a one-time flag, so the four equipment points are awarded only once.
8. Board the *Sea Farer* directly in Brooklyn. Do not take the ferry sequence,
   which belongs to the overland departure. The ship's checkpoint must report
   60 out of 60.

### Panama crossing: 40 points

1. Disembark near the Rio Chagres and proceed with the guide. Wear or retain
   the mosquito net whenever the route checks it.
2. When armed people demand the party's valuables, answer yes and cooperate.
   The completed negotiation awards four points. Refusal reaches the spear
   death.
3. Continue from the river boat onto the old Spanish road. When jungle ants
   cover the path, escape by the hanging vine. Completing that event awards
   four points.
4. Speak to the resting traveler under the tree and accept his Bible. The
   conversation and acquisition are alternate parser entries for the same
   seven-point award, not two awards.
5. Take the higher-valued successful jungle traversal branch. Its five-point
   award replaces the three-then-two alternative state sequence.
6. Search the densely overgrown old gold route, expose the ancient Spanish
   gold disk, and take it for ten points.
7. Cross the later stream hazard successfully for ten points. Avoid the swamp
   and concealed alligator branches.
8. Reach the California arrival sequence at exactly 100 points. The checkpoint
   explicitly excludes the optional Psalm 23 award. Once the Bible read is
   enabled, read Psalm 23 for the separate five points.

### Sacramento, Sutter's Fort, and the hotel

1. Board the one available Sacramento stage to Sutter's Fort before it leaves.
   The approach/boarding sequence contains two separate one-point awards.
2. Read the relevant Sutter's Fort gravestone for two points. Hold Jake's open
   letter against the Wilson Marshall stone so its holes reveal `ROOM 11`; this
   clue sequence awards five.
3. At the blacksmith, answer the family questions with Jerrod's identity and
   Jake's name. Receive the branding iron and learn that Jake is known locally
   as James. The completed recognition sequence awards two points.
4. Obtain a gold pan, lantern, and shovel. Pay for the shovel with the Brooklyn
   gold coin for one point; never offer the ancient disk. Find enough ordinary
   California gold to buy the mule, then take the purchased mule for three.
5. Heat and use the branding iron on the mule for three points. Stable it and
   later identify the same branded animal; the successful corral check awards
   seven.
6. In the City Hotel, deliver the confidential message to the person emerging
   from room 11 before he walks away for three points.
7. Recover the robbery trail in the hotel room. Rotate the decorative cannon
   wheel to raise the fireplace wall for five points. Recover the note from
   Jake, magnet, string, and gold coin for one point each. Complete the bird
   capsule exchange: obtain the aerogram for one point and place the family
   photograph in the capsule for three. The duplicate cannon score in the
   adjacent room is the same one-time event.
8. Follow the clue state until James' distinctive old mule appears. Begin
   following it in an eligible wilderness room for seven points and keep close
   through each direction change. Losing either mule can strand the route.

### Cabin and mine

1. Enter James' cabin and take the matches from the table for one point. Move
   the central rug, expose the trap door, and descend through the outhouse/mine
   approach; the committed descent sequence awards three.
2. At the locked mine door, tie the string to the magnet for two points. Put it
   through the hole, lower it, and pull it back up, receiving two points at
   each stage and retrieving the steel key. Unlock the double lock for one.
   The complete door chain is nine points.
3. Keep a light available. The mine scripts distinguish lantern light, a
   briefly lit match, and darkness; darkness hides traversable geometry and
   introduces falls. Take the pick when it appears for one point.
4. Traverse each distinct scored mine boundary. Rooms 151, 152, 154, 156, 157,
   158, and 160 each contribute one first-crossing point; room 161 contributes
   two independent crossings; room 162 contributes three. Opposite-direction
   code paths set the same per-boundary state and are alternatives, not extra
   awards.
5. Search, strike, and collect gold at valid sites throughout California and
   especially the deep mine. Each successful increase advances the displayed
   gold amount and awards one point until the shared counter reaches 70. Do
   not leave this grind until all 70 awards have been obtained.
6. Continue to the end of James' mine. Avoid the five-point failure branch in
   logic 162. Break through toward the sound of picking, reunite with James,
   and work the final wall until the pure-gold vein sequence begins. Logic 193
   adds six points on the Panama route and ends the game at 255.

## Score Ledger

The ledger groups sequential awards and collapses route alternatives and
duplicate room copies.

| Chain | Points |
| --- | ---: |
| Brooklyn documents: postmark, stamp, statement read | 4 |
| Early house sale | 9 |
| Gold coin and flowers | 6 |
| Family gravestones and flower placement | 5 |
| Travel sign | 2 |
| Post-office letter | 5 |
| Family photograph, statement retrieval, and album | 8 |
| Newspaper clipping and quitting | 5 |
| Bank withdrawal | 3 |
| Panama ticket | 9 |
| Mosquito net | 4 |
| Panama negotiation, ant/vine escape, and Bible | 15 |
| Best jungle traversal, ancient disk, and stream crossing | 25 |
| Psalm 23 | 5 |
| Sacramento stage | 2 |
| Blacksmith recognition and mule branding | 5 |
| Mule purchase, shovel purchase, and corral identification | 11 |
| Gravestone and perforated-letter clue | 7 |
| Hotel message delivery and recovery/capsule puzzle | 16 |
| Begin following James' mule | 7 |
| Cabin matches and committed descent | 4 |
| Magnet/string/key door puzzle | 9 |
| Mine pick and distinct boundary discoveries | 13 |
| Gold-amount progression cap | 70 |
| Final Panama-route ending award | 6 |
| **Total** | **255** |

The raw score-site list is much larger because it combines three travel
routes, opposite-direction copies, parser synonyms, alternate payment media,
and penalty branches. In particular, the four ferry points belong to the
overland departure, the Cape ship survival puzzles do not occur on Panama,
and spending the ancient disk subtracts points.

## Deaths, Losses, and Dead Ends

The resources expose at least these replay-relevant failure families:

- missing timed departures in Brooklyn or Sacramento;
- walking repeatedly on park grass or selling the house after its value falls;
- boarding without the correct ticket or required route-specific supply;
- refusing the Panamanian demand, losing time to jungle disease, falling to
  ants, snakes, alligators, swamp, or other route hazards;
- spending the ancient disk, buying insufficient supplies, losing a mule, or
  selecting an incorrectly branded mule;
- missing the room-11 recipient, losing the hotel/capsule clue chain, or
  abandoning the magnet, string, matches, lantern, key, or pick;
- entering dark mine geometry, falling, taking the explicitly scored failure
  branch, or reaching the ending before exhausting the 70 gold awards;
- continuing to add score after the intended byte total, which risks wrapping
  the displayed score rather than producing a higher terminal result.

## Replay Requirements

A deterministic original-interpreter playthrough should record at least:

1. the pre-rush nine-point house sale and the 60-point ship checkpoint;
2. each Panama route hazard and the 100-point California checkpoint;
3. the Psalm 23 award as a separate post-checkpoint event;
4. robbery inventory before and after the hotel recovery sequence;
5. mule purchase, branding, corral identity, and James-mule follow state;
6. every magnet/key transition and first-time mine boundary award;
7. gold amount, gold-award counter, and score at the outside-50 and mine-70
   thresholds;
8. reunion, final six-point mutation, displayed 255 maximum, and terminal
   thank-you state.

The replay should also deliberately exercise one missed departure, one jungle
death, one ancient-disk payment, one wrong-mule selection, and one dark-mine
fall. These are useful negative conformance scenarios, but are not steps in the
winning route.
