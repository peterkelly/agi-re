# King's Quest 4 Playthrough Analysis

This chapter records a game-specific, clean-room reconstruction of a maximum-
score winning playthrough for the local full `KQ4` evidence set. It is intended
to become a repeatable conformance scenario, not part of the portable AGI
engine specification. The route was derived from the game's logic, messages,
vocabulary, objects, pictures, views, and local copy-protection answer text. No
external walkthrough or AGI documentation was consulted.

The result is currently a **static candidate route**. Script control flow,
parser vocabulary, inventory transformations, score mutations, room
transitions, and ending messages support a complete 230-point route. Exact
movement, day/night timing, random encounters, and the final input stream still
require replay under the original interpreter.

## Evidence Method

The reusable playthrough index can be generated with:

```bash
AGI_GAME_DIR=games/KQ4 \
  python3 -B tools/logic_playthrough_index.py \
  --output build/playthrough/kq4/index.json
```

The full game uses interpreter 3.002.086 and the v3 combined directory and
prefixed-volume container. The index contains 177 readable logic resources,
5,148 parser conditions, 469 room transitions, 86 score mutations, and 45
inventory slots. No present logic failed to decode. Logic 101 assigns **230**
as the declared maximum score.

KQ4 exposed a storage-dependent message rule in the reusable tooling. Its 174
dictionary-expanded logic records contain plain expanded message text, while
its three direct records (97, 100, and 131) retain the repeating-key encoding.
The local executable sets a direct-read flag at image `0x331b`, clears it after
dictionary expansion at `0x3348`, and conditionally calls the XOR helper from
logic setup at `0x1458..0x148c`. The indexer and disassembler now select message
decoding from that record transform.

All 146 locally readable pictures were decoded into a qualitative contact
sheet. Pictures 150 and 151 cannot be read because the selected private copy
does not contain `KQ4VOL.6`. The current local renderer's patterned-brush table
offsets are SQ2-specific, so the KQ4 sheet deliberately disables patterned
brushes. It corroborates geography and interiors but is not pixel-conformance
evidence.

## Story and Winning State

King Graham collapses while offering his adventurer's hat to Alexander and
Rosella. Genesta transports Rosella to Tamir and explains that a fruit from the
Tree of Life can save Graham, but the evil fairy Lolotte has stolen Genesta's
talisman and left her dying. Rosella must recover the talisman before Genesta
can send her home.

Lolotte forces Rosella through three errands: capture the unicorn, steal the
ogres' magic hen, and retrieve Pandora's Box. The promised reward is a forced
marriage to Lolotte's son Edgar. Edgar secretly supplies the key that lets
Rosella escape, recover her possessions, kill Lolotte with Cupid's remaining
arrow, and reclaim the talisman.

Returning the talisman to Genesta selects the successful ending only if
Rosella also has the healing fruit. The ending restores Genesta, returns the
hen, rewards Edgar, sends Rosella home, and reaches logic 138. Messages 24--29
show Rosella giving Graham the fruit, Graham recovering, and the family
declaring that he is not done with the adventurer's hat. The conformance route
must enter this terminal sequence with score **230**.

## Global Constraints

The route crosses several persistent state boundaries:

1. Day gives way to night, enabling the haunted-house ghost sequence. Morning
   eventually closes that opportunity.
2. The shovel has limited useful digs. Dig only the five graves identified by
   their epitaphs; unnecessary digs risk replacing it with the broken shovel.
3. The undead retreat only while Rosella carries the obsidian scarab. The dark
   cave and crypt also require the dwarf's lantern.
4. Cupid supplies exactly two arrows. One befriends the unicorn and the other
   kills Lolotte. Firing either elsewhere destroys the winning route.
5. The board is reused at the waterfall crevice and in the swamp. Pick it up
   after crossing and never abandon it before obtaining the fruit.
6. Taking or opening Pandora's Box is dangerous story state. For maximum score,
   recover it from Lolotte and return it to its tomb before visiting Genesta.
7. After the third Lolotte errand, dawn leads to the forced-wedding loss. Escape
   Edgar's room and kill Lolotte during the available night.
8. Returning the talisman without the fruit produces a completed Tamir rescue
   but Graham dies. Eating or losing the fruit likewise prevents the winning
   terminal state.

## Candidate Route

### Tamir tools and trading chains

1. Accept Genesta's request and explore Tamir. Look under the stone bridge and
   take the golden ball for two points.
2. At Cupid's pool, approach or speak closely enough to startle Cupid away,
   then take the abandoned golden bow and two arrows for two points. Do not
   fire either arrow yet.
3. At the frog pond, catch the crowned frog. While holding it, take its crown
   for two points. Let the frog return, catch it again, and kiss it. The
   transformation sequence awards three points and the departing prince's
   crown sequence awards two more. This seemingly redundant order is required
   for the 230-point route: taking the crown directly and kissing the frog are
   separate scored branches, and the catch parser does not require the crown
   to remain on the frog.
4. Enter the old manor's parlor. Take *The Compleat Works of William
   Shakespeare* for two points. Examine the portrait, follow its gaze to the
   left wall, and flip the small latch to reveal the secret stair for four.
   Take the shovel in the secret tower for two.
5. Give the Shakespeare book to the wandering minstrel for his lute and three
   points. Play the lute near Pan to attract him, then give it to him for the
   silver flute and three points.
6. Enter the ogres' house only while it is safe. Take the sharp axe from the
   upstairs bedroom for two points. Use it against the grabbing trees; their
   retreat is worth four.
7. Clean the Seven Dwarfs' home before they return: use the broom, sweep and
   tidy the rooms, clean the dishes, make the beds, and hide the dirty clothes
   under the rug. Completion awards five points. After the dwarfs eat and
   leave, take the forgotten diamond pouch for two.
8. At the mine, offer the pouch back to a dwarf. He refuses to keep it, gives
   Rosella an oil lantern, and awards three points. The pouch remains available
   for the next trade. Light or extinguish the lantern with its attached flint
   as needed.
9. Give the diamond pouch to either member of the fisherman's household. They
   exchange it for the fishing pole and three points.
10. Take the earthworm when the robin exposes it for two points. Baiting the
    fishing pole with the worm awards one. Cast from the pier and catch the
    dead fish for three.

### Island and waterfall chain

1. Give the fish to the pelican on the desert island for four points. Take the
   dropped silver whistle for two, blow it for two, and ride the summoned
   dolphin for two.
2. Search the wrecked boat and take the golden bridle for three points. On
   Genesta's island, take the peacock feather for two.
3. The ocean route eventually places Rosella inside the whale. Tickle its
   throat with the peacock feather to trigger the sneeze and escape for five
   points. Avoid the whale's fumes, drowning, and the shark while traveling.
4. Enter the waterfall pool and force through the current to discover the cave
   behind the waterfall for five points. Take the board for two and the bone
   from the next cave for two. Use the board across the dark crevice, retrieve
   it after crossing, and cross back later; the first two successful crossings
   advance a two-stage counter and award two points each.

### Witches, graves, and crypt

1. In the witches' cave, seize their shared glass eye for three points. Leave
   and return while they are blind; they throw down an obsidian scarab. Take it
   for two, then return the eye for three. Carry the scarab whenever undead are
   active.
2. At night, use the shovel only on the five epitaph-matched graves: the baby,
   old miser, sad young woman, lord of the manor, and little boy. Recover the
   silver rattle, bag of gold, locket, Medal of Honor, and toy horse. Each
   correct dig awards three points, for fifteen total.
3. Follow each ghost into the manor and return its matching possession: rattle
   to the baby cradle, gold to the miser, locket to the woman, medal to the
   lord, and toy horse to the boy. Each resolution awards two points. Once the
   boy leaves the attic chest, open it and take the sheet music for another two.
4. Sit at the dusty pipe organ and play from the sheet music. The correct tune
   opens its hidden drawer for four points; take the skeleton key for two.
5. Use the skeleton key to unlock the mountainside crypt for three points.
   Carry the lit lantern and scarab, descend the rope ladder, and drive off the
   mummy. Reaching the lower tomb awards two points. Taking Pandora's Box
   subtracts two and then awards four on the first valid acquisition, a net two.
   Preserve the box for Lolotte's third errand.

### Tree of Life

1. Take the recovered board through the waterfall cave and across both
   crevices to the swamp. Place it from a safe grass tuft to the Tree of Life
   island for two points.
2. Play Pan's flute to mesmerize the cobra for four points. Cross promptly and
   take the magic fruit for ten. Recover the board where required and keep the
   fruit uneaten.

### Lolotte's three errands

1. Approach Lolotte's mountain domain and allow her henchmen to bring Rosella
   before the throne. Lolotte orders the capture of the unicorn.
2. At the unicorn meadow, shoot exactly one Cupid arrow at the unicorn. The
   love arrow makes it trust Rosella and awards four points. Fit the golden
   bridle for three, mount, and ride it to Lolotte. The first completed errand
   awards seven points.
3. For the second errand, return to the ogres' house with the cave bone. Give
   the bone to the dog for four points. Wait for the ogre to sleep, take the
   magic hen from the locked bedroom area without waking him, and escape for
   four. Delivering the hen to Lolotte awards the second seven points.
4. Deliver Pandora's Box for the third errand. Lolotte awards another seven
   points, confiscates Rosella's possessions, and locks her in Edgar's tower
   room to await the morning wedding.

### Escape, restoration, and ending

1. Wait for Edgar's red rose to slide under the door. Take it, remove the
   hidden gold key for two points, and use that key to unlock Edgar's door for
   two.
2. In the castle kitchen, open the cabinet and recover all confiscated
   possessions for four points. Use the gold key to unlock Lolotte's tower door
   for two.
3. While Lolotte sleeps, shoot the second and final golden arrow at her. Her
   incompatibility with the arrow's love kills her and awards eight points.
   Take Genesta's talisman from her body for five.
4. Recover Pandora's Box and the magic hen from the storage room for two points
   each. Open the stable gate and free the imprisoned unicorn for four.
5. Return Pandora's Box to the floor of its lower tomb for two points. Exit the
   crypt, lock its door, and kick the skeleton key underneath for two. These
   steps restore the dangerous object and complete the crypt score chain.
6. Visit Genesta carrying the talisman, hen, and uneaten fruit. Giving her the
   talisman awards ten points and starts the ending. Returning the hen during
   the ending awards two. Genesta restores Edgar, sends Rosella home, and the
   final sequence gives the fruit to Graham at score 230.

## Score Ledger

The following grouped ledger preserves sequential awards while collapsing
alternate room copies of the same parser branch.

| Chain | Points |
| --- | ---: |
| Golden ball; direct frog crown; frog-kiss transformation and prince sequence | 9 |
| Cupid's bow and arrows | 2 |
| Shakespeare book, secret latch, and shovel | 8 |
| Book-to-minstrel and lute-to-Pan exchanges | 6 |
| Ogre axe and grabbing-tree retreat | 6 |
| Dwarf-house cleaning, diamond pouch, and honest mine return | 10 |
| Diamond-pouch fishing-pole trade | 3 |
| Worm, baiting, and fish catch | 6 |
| Pelican, whistle pickup/use, and dolphin mount | 10 |
| Golden bridle, peacock feather, and whale escape | 10 |
| Waterfall discovery, board, bone, and two crevice crossings | 13 |
| Glass eye seizure/return and scarab | 8 |
| Five correct grave digs and five resolved ghosts | 25 |
| Sheet music, organ drawer, and skeleton key | 8 |
| Crypt unlock, lower tomb, first Pandora acquisition, later return, and relock | 11 |
| Swamp board placement, cobra flute, and healing fruit | 16 |
| Unicorn love arrow and bridle | 7 |
| Dog distraction and magic hen | 8 |
| Three Lolotte errands | 21 |
| Edgar-room rose/key and door | 4 |
| Recovered possessions and Lolotte tower door | 6 |
| Lolotte death and talisman | 13 |
| Recovered box and hen; freed unicorn | 8 |
| Talisman and hen returned to Genesta | 12 |
| **Total** | **230** |

The raw sum of all positive sites is 267. The excess consists of duplicated
Pan, minstrel, grabbing-tree, fisherman, book-position, crossing-direction,
and grave-location code paths. The direct crown action is not discarded as a
duplicate: after the frog returns, it can be caught again and kissed, so both
that two-point action and the five-point transformation sequence belong to the
maximum route.

## Deaths, Losses, and Dead Ends

The resources expose at least these replay-relevant failure families:

- drowning, shark attack, whale fumes, and getting stranded during ocean
  travel;
- entering grabbing-tree, ogre, dog, witch, zombie, mummy, troll, or cobra
  hazards without the corresponding axe, bone, scarab, lantern, flute, or safe
  timing;
- bad grave digs that exhaust the shovel before all five ghost possessions are
  recovered;
- falling in darkness, stepping into swamp quagmires, or remaining beside the
  cobra after its temporary trance ends;
- wasting either golden arrow, abandoning a one-use chain item, opening or
  mishandling Pandora's Box, or eating the healing fruit;
- waking Lolotte, failing to escape before morning, or reaching the forced
  wedding;
- returning the talisman without the fruit, which saves Genesta and Tamir but
  reaches the explicit ending where Graham dies.

## Replay Requirements

A deterministic original-interpreter playthrough should record at least:

1. score and inventory after the social/trading chains;
2. day-to-night transition and each grave/ghost pair;
3. crypt entry, first Pandora acquisition, and later restoration;
4. fruit acquisition with board and flute state;
5. each Lolotte errand at cumulative quest-state values 1, 2, and 3;
6. confiscation, rose delivery, possession recovery, and the two arrow uses;
7. restored unicorn, box, hen, talisman, and fruit state before Genesta; and
8. logic 138's healthy-Graham terminal sequence at score 230.

The replay must also settle exact movement coordinates, random encounter
control, day/night timing, and whether the unusual crown-then-recatch sequence
needs any delay or room transition under the original interpreter.
