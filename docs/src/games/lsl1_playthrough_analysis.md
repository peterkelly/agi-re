# Leisure Suit Larry 1 Playthrough Analysis

This chapter records a game-specific, clean-room reconstruction of a maximum-
score winning playthrough for the local `LSL1` evidence set. It is intended to
become a repeatable conformance scenario, not part of the portable AGI engine
specification. The route was derived only from the game's logic, messages,
vocabulary, objects, pictures, and views. No external walkthrough or AGI
documentation was consulted.

The result is currently a **static candidate route**. All score operations,
inventory dependencies, money gates, major parser actions, and the terminal
sequence are accounted for at 222 points. Exact movement, random age questions,
casino outcomes, and the final timed input stream still require replay under
the original interpreter.

## Evidence Method

The reusable playthrough index can be generated with:

```bash
AGI_GAME_DIR=games/LSL1 \
  python3 -B tools/logic_playthrough_index.py \
  --output build/playthrough/lsl1/index.json
```

The selected game identifies itself as *Leisure Suit Larry in the Land of the
Lounge Lizards*, version 1.00 dated June 1, 1987. It uses interpreter 2.440.
The split directories contain 46 readable logic resources, 43 pictures, 151
views, and 28 sounds. The index found 2,274 parser conditions, 16 explicit room
switches, 21 inventory slots, and 49 positive score operations. No present
logic resource failed to decode.

Logic 51 assigns **222** as the displayed maximum. The 49 positive score
operations also sum to exactly 222, and the game contains no negative score
operation. Direct inspection shows that every award belongs to the maximum
route; there is no duplicate score-site reduction analogous to the other games
analyzed so far.

Logic 45 contains the terminal sequence. After the final penthouse encounter,
it awards 25 points, displays `Congratulations, Larry!!!`, states that Larry
has completed the evening and emerged victorious, reports his performance,
and presents the closing credits and sequel promotion. This is the winning
terminal state used by this analysis.

All 43 present pictures decoded in a qualitative sweep with patterned brushes
disabled. The resulting sheet covers Lost Wages streets, Lefty's, the hooker's
room and fire escape, convenience store, disco, casino, chapel, hotel,
honeymoon suite, upper-floor security desk, penthouse, rooftop spa, and final
bedroom. This historical sheet was rendered with brushes disabled and remains
qualitative evidence. The later interpreter audit maps LSL1's v2 mask and
pointer tables at `0x1575` and `0x1595`; the renderer can now discover them
without an SQ2-specific offset.

## Story and Winning State

Larry Laffer enters Lost Wages with $94 and attempts to end the night no longer
a virgin. His route passes through Lefty's bar and its upstairs room, the
convenience store, disco, casino, wedding chapel, and casino hotel. The first
encounter does not satisfy him. Fawn accepts gifts and money, marries Larry,
then robs him after tying him to the honeymoon-suite bed. The rope from that
escape enables Larry to recover pills from Lefty's fire escape. Those pills
distract hotel guard Faith and expose the private penthouse control. In the
penthouse, Larry meets Eve in the rooftop spa, gives her an apple, follows her
to the bedroom, and reaches the terminal winning sequence.

## Global Constraints

1. Pass the initial adult-verification quiz. The game chooses questions at
   runtime, so a deterministic replay must either answer from the decoded
   question/answer table or control the random sequence.
2. Preserve enough cash for cab fares, store purchases, the apple, Fawn's
   $100 request, and the separate $100 chapel fee. The casino must fund the
   route; both slot machines and blackjack are random without a controlled
   replay strategy.
3. Do not give wine to the cab driver. He becomes impaired and crashes into a
   bridge abutment. Pay each fare before leaving the cab.
4. Buy and use the prophylactic before the first upstairs encounter. That
   encounter transforms it into the used item; dispose of the used item for
   the separate one-point award.
5. Carry rather than drink Lefty's whiskey. The hallway drunk exchanges the
   drink for the remote control needed to bypass the pimp without paying $100.
6. Keep the rose, candy, and diamond ring for Fawn. Each is a separate
   five-point gift, and the ring is also required by the wedding ceremony.
7. Obtain the pocket knife by giving the convenience-store wine to the outside
   drunk. Without the knife, Fawn's bed ropes form a terminal dead end.
8. Turn on the honeymoon-suite radio and hear the Ajax Liquor advertisement
   before leaving. It supplies `555-8039`, needed to order Fawn's wine.
9. After escaping Fawn, take the rope. Combine its reach with the hammer from
   Lefty's trash to break the remote window and recover the pills.
10. Complete the inflatable-doll sequence before the final encounter. Taking,
    inflating, and using it account for 18 points independent of the 25-point
    winning sequence.
11. The game is real-time. Logic 19 ends the night at sunrise if the route
    takes too long, so a replay must bound casino play and travel delays.

## Candidate Route

### Lefty's and the first encounter

1. Enter Lefty's and visit the restroom. Sit on the toilet, read the graffiti
   until it reveals the password **Ken sent me**, examine the sink, and take
   the diamond ring.
2. At the bar, sit down and order whiskey. Do not drink it; carry the filled
   glass. In the back hallway, take the rose and give the whiskey to the drunk.
   He eventually gives Larry the remote control.
3. Return to the bar and use the restroom password at the naugahyde door.
   In the storage room, use the remote on the television and change channels
   until the program distracts the pimp. Pass him and go upstairs without
   paying his $100 demand.
4. In the bedroom, take the box of candy. Put on the prophylactic before
   approaching the hooker, then complete the encounter. Afterwards, dispose of
   the used prophylactic and read the centerfold when the magazine is available.
5. Leave through the window to the fire escape. Search the trash and take the
   hammer. The pills in the other window cannot yet be reached safely; Larry
   must return after obtaining Fawn's rope.

### Store, telephone, and travel preparation

1. At the convenience store, take the bottle of wine and the `Jugs` magazine.
   Ask the clerk for a prophylactic, complete his option sequence, and pay for
   it. Read the magazine for its separate one-point award.
2. Outside, examine the telephone and its markings. Call `555-6969`, complete
   the survey prompts, and later answer the returning call. Call Sierra at the
   decoded number for the five-point promotional conversation.
3. Give the bottle of wine to the drunk outside the store. He gives Larry his
   pocket knife. Preserve it through the wedding and hotel sequence.
4. Take at least one cab ride and pay the fare; the first completed ride awards
   one point. Never offer the driver wine.

### Casino, disco, and Fawn

1. At the casino entrance, buy the apple from the vendor. In the hotel lobby,
   take the disco pass from the ashtray.
2. Gamble until Larry can preserve at least $200 beyond remaining travel and
   purchase costs. Slot-machine and blackjack outcomes do not award score, but
   they gate Fawn's $100 request and the chapel's independent $100 fee.
3. Show the pass to the disco bouncer. Inside, trigger the comedian's scored
   whoopie-cushion event, then sit with the blonde woman. Establish eye contact,
   ask her name, and dance with her.
4. Give Fawn the rose, box of candy, and diamond ring. Give her $100 when she
   requests the honeymoon-suite money. She directs Larry to the wedding chapel.
5. Outside the chapel, speak to the man in the trench coat for the one-point
   encounter. Inside, stand in the required position with Fawn, retain the
   ring state, and pay the minister the separate $100 fee. Complete the wedding
   ceremony.

### Fawn and the rope

1. Go to the casino hotel's heart-marked honeymoon suite. Turn on the radio and
   listen through the Ajax Liquor advertisement, learning `555-8039` for one
   point.
2. Return to an outside telephone, call Ajax, order wine, and specify the
   honeymoon suite. The completed delivery call is worth five points. Return
   to Fawn after the delivery.
3. Pour the wine for Fawn and follow her instructions. She ties Larry to the
   bed, takes his visible wallet money, and leaves. Use the pocket knife to cut
   the ropes, then take the freed rope. Cutting and taking it award 10 and 3
   points respectively.
4. Return to Lefty's fire escape. Tie the rope for safety, reach toward the
   remote window, use the hammer to break the glass, and take the bottle of
   pills. The hammer and pill acquisitions are worth 3 and 8 points.

### Faith, Eve, and the penthouse

1. Ride the hotel elevator to the guarded upper floor. Establish eye contact
   and speak with Faith, then give her the pills. After she consumes them and
   leaves, press the previously guarded unlabeled desk button. The two actions
   award five points each and open the private penthouse elevator.
2. Enter the penthouse and explore the bedroom closet before completing the
   rooftop encounter. Take the inflatable doll, inflate it, and use it as the
   parser permits. These steps award 5, 5, and 8 points.
3. Follow the gurgling sound to the rooftop spa. Enter the water, establish
   contact with Eve, and give her the apple. The completed apple sequence
   awards 15 points. Follow Eve from the spa into the penthouse bedroom.
4. Complete the bedroom sequence. Logic 45 awards the final 25 points and
   enters the congratulatory terminal state at **222 of 222**.

## Score Ledger

Every positive score site is included exactly once.

| Chain | Points |
| --- | ---: |
| First completed cab ride | 1 |
| Read centerfold and dispose of used prophylactic | 2 |
| Lefty's restroom: sit, password graffiti, ring | 6 |
| Hallway rose and whiskey-for-remote exchange | 3 |
| Carry Lefty's whiskey | 1 |
| Remote-control television and bypass pimp | 11 |
| Candy, protected encounter, and first completion | 23 |
| Fire-escape hammer and pills | 11 |
| Store wine, magazine, and prophylactic purchase | 6 |
| Telephone number, drunk exchange, and four call events | 23 |
| Casino-lobby disco pass and bouncer admission | 6 |
| Lounge comedy event | 1 |
| Sit and dance with Fawn | 6 |
| Eye contact, name, three gifts, and Fawn's money | 24 |
| Apple vendor and chapel stranger | 4 |
| Wedding ceremony | 12 |
| Radio advertisement, rope escape, and rope acquisition | 14 |
| Faith's pills and penthouse control | 10 |
| Eve's apple sequence | 15 |
| Doll acquisition, inflation, use, and final encounter | 43 |
| **Total** | **222** |

## Failure and Dead-End Map

- Failing the adult quiz prevents play from starting.
- Sunrise ends the game while Larry remains unsuccessful.
- Losing all casino money leaves Larry unable to pay travel and story gates;
  the zero-money sequence ends with Larry on skid row.
- Giving wine to the cab driver causes a fatal crash.
- Shoplifting prompts the store clerk to shoot Larry.
- Omitting the prophylactic makes the first encounter unsafe and prevents the
  protected-item score chain.
- Drinking the hallway whiskey or discarding Fawn's gifts blocks later item
  dependencies.
- Entering Fawn's suite without the pocket knife leaves Larry tied permanently.
- Missing the radio advertisement leaves no in-game source for Ajax's number.
- Using the aphrodisiac pills on Larry produces an unrelated fatal/failure
  branch; they must be given to Faith.
- Touching Faith's button before distracting her causes her to shoot Larry.

## Replay Work Remaining

1. Extract the randomized adult-question answer table into a deterministic
   replay helper.
2. Choose and validate a bounded casino strategy that reliably finances the
   route before sunrise.
3. Record exact parser strings for store options, calls, cab destinations,
   Fawn's conversation, Ajax delivery, and the final bedroom sequence.
4. Map movement coordinates and timing around the hooker's bed, fire escape,
   disco, elevator, Faith's desk, spa, and penthouse bedroom.
5. Run the complete route under interpreter 2.440 and package room, inventory,
   cash, score, and terminal-state checkpoints as a conformance scenario.
