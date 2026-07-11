# Police Quest 1 Playthrough Analysis

This chapter records a game-specific, clean-room reconstruction of a winning
playthrough for the local `PQ1` evidence set. It is intended to become a
repeatable conformance scenario, not part of the portable AGI engine
specification. The route was derived only from the game's logic, messages,
vocabulary, objects, pictures, views, and two read-only local save files. No
external walkthrough or AGI documentation was consulted.

The story route is complete from the opening roll call through the terminal
parade. It is currently a **static candidate route**, rather than a validated
input replay. The game declares a maximum score of 245. The positive score
operations sum to 270 before alternatives are removed; several shared and
losing branches are classified below, but the exact 245-point ledger still
needs a source-level reachability pass and an original-interpreter replay.

## Evidence Method

The reusable playthrough index can be generated with:

```bash
AGI_GAME_DIR=games/PQ1 \
  python3 -B tools/logic_playthrough_index.py \
  --output build/playthrough/pq1/index.json
```

The selected game identifies itself as *Police Quest: In Pursuit of the Death
Angel*, version 2.0G dated December 3, 1987. It uses interpreter 2.917. Its
split directories contain 118 readable logic resources, 71 pictures, 220
views, and 36 sounds. The index found 3,147 parser conditions, 108 explicit
room transitions, 25 inventory slots, and 114 positive score operations. No
present logic resource failed to decode.

Logic 101 assigns **245** as the displayed maximum. Logic 79 captures Jessie
Bains after the successful hotel-room confrontation. Logic 103 depicts his
trial and sentencing and awards four points late in that sequence. Logic 104
then shows the ticker-tape parade, presents Sonny with the Key to the City,
and displays `Congratulations. You've won Police Quest!`. That is the terminal
winning state used by this analysis.

Two bundled saves were inspected as independent consistency evidence only.
Both preserve score 156 of 245 near the hotel operation, with the Tribune,
Hoffman file, trick cane, marked money, room key, and Cadillac keys in
inventory. They corroborate the decoded save-state and inventory
interpretation, but they do not define the route or prove a maximum score.

All 71 present pictures decoded in a qualitative sweep with patterned brushes
disabled. The resulting sheet covers the station, patrol map, traffic and
accident sites, Blue Room, cafe, jail, courthouse, park, Cotton Cove, Hotel
Delphoria, poker rooms, and ending locations. PQ1's own patterned-brush table
was not mapped when the sheet was generated, so these renders establish
geography only and are not pixel-conformance evidence. The later audit maps
its v2 mask and pointer tables at `0x15ef` and `0x160f`.

## Story and Winning State

Sonny Bonds is a veteran patrol officer in Lytton. Routine patrol exposes a
connected series of crimes: murdered drug dealer Lonny West, cocaine reaching
local students, a stolen Cadillac driven by Marvin Hoffman, and a street
informant's warning about a trafficker called the Death Angel. Fingerprints
and records identify Hoffman as Jason Taselli and connect the organization to
Jessie Bains.

After a park narcotics arrest and Kathy Cobb's fatal overdose, Sonny transfers
to Narcotics. Hoffman/Taselli is later found murdered at Cotton Cove. Sonny
works undercover at the Hotel Delphoria as Jimmy Lee Banksten, called
`Whitey`, using bleached hair, a white suit, a cane concealing a derringer,
marked money, and a transmitter pen. Sweet Cheeks introduces him to bartender
Woody Roberts. Sonny buys entry to the back-room poker game, wins an invitation
to the high-stakes game, identifies Bains, and transmits the room number to
backup officers. The successful confrontation captures Bains alive. His
conviction, sentence, and Sonny's parade constitute the winning state.

## Global Constraints

1. Attend both patrol briefings and the later Narcotics briefings. Lateness or
   insubordination can terminate employment, while missed briefings suppress
   the state transitions needed for later calls.
2. Follow police procedure. Keep the service revolver loaded on patrol, unload
   and secure it before entering the jail, search suspects, read rights,
   handcuff behind the back, and preserve evidence. Several shortcuts are
   immediately fatal.
3. During the first traffic stop, reject Helen Hots' offer and complete the
   citation. Accepting her proposition is a scored but corrupt branch and does
   not belong to the successful police-procedure route.
4. Inspect and call in clues while they are available. The bullet hole,
   license plates, vehicle identification number, gun, drugs, fingerprints,
   Hoffman file, wanted poster, computer record, and phone calls advance
   separate one-time states.
5. Obtain the no-bail warrant before Hoffman's attorney completes bail, and
   deliver it at the jail. The warrant delays his release long enough for the
   investigation even though the later story still finds him murdered.
6. Search and question the park suspects before completing the arrests. Ask
   for the friend's name and question Colby about his supplier; these select
   the higher-valued shared information branch and expose Leroy Pierson.
7. Preserve the undercover equipment and use the alias Jimmy Lee Banksten at
   the hotel. Pay for the room with marked money and do not reveal Sonny's
   identity to hotel personnel.
8. Send Sweet Cheeks away before the high-risk portion of the operation. Buy
   Woody's cooperation, follow him to the back room, and win the preliminary
   poker sequence to obtain the invitation/password.
9. Contact Lieutenant Morgan and transmit `Room 404` before entering Bains'
   room. The earlier transmitter path awards five points; the later telephone
   fallback awards only two and is an alternative guarded by the same state.
10. Do not confront Bains without armed backup. The successful room sequence
    requires the prior transmitter, backup setup, poker invitation, and Bains
    identification states.

## Candidate Route

### First patrol shift

1. At the station, attend Sergeant Dooley's briefing in the assigned place.
   Check Sonny's pigeonhole, take and later read the *Lytton Tribune*, and
   collect the patrol equipment: revolver, ammunition, briefcase, keys, radio
   extender, wallet, and nightstick. Load the revolver, take the notebook, pen,
   and ticket book from the briefcase, and perform the patrol-car walk-around.
2. Respond to the red-light runner. Stop the car, approach the driver, identify
   Sonny, request and inspect Helen Hots' license, and call in the plate. Say
   no to her attempted bargain. Write the citation, hand her the ticket book
   and pen for a signature, recover them, return her license, and complete the
   stop without accepting the proposition.
3. At the traffic accident, secure and inspect the scene. Examine the victim,
   car, window, bullet hole, and identifying details; call Dispatch and treat
   the site as a homicide rather than an ordinary collision.
4. Meet Jack at the Blue Room and remain for the scored conversation and shift
   reminder. At Carol's Caffeine Castle, answer Detective Hamilton's phone
   call, resolve Carol's complaint, and deal with the bikers. Question Sweet
   Cheeks about cocaine and information until she identifies the Death Angel
   and the flower-tattoo clue.

### DUI and Hoffman arrests

1. Return for the next briefing and read the transfer memo. On patrol, stop
   the erratically driven vehicle. Check the license and plate, administer the
   field sobriety test, arrest the driver for DUI, read his rights, search him,
   and handcuff him behind his back.
2. Before entering the jail, lock the revolver in the gun locker. Book the
   drunk, transfer his property, remove the handcuffs only when directed, and
   retrieve the secured weapon afterward.
3. Respond to the stolen light-blue Cadillac report using felony-stop
   procedure. Draw the revolver, order the driver out, control his position,
   handcuff him, read his rights, search him, and recover his handgun. Inspect
   the door-jamb vehicle number and trunk drugs. Call in the vehicle and gun.
4. At the jail, secure Sonny's gun before booking Hoffman. Complete the booking
   and uncuffing sequence. Search the station evidence and records, take the
   Cadillac keys and Hoffman file, inspect Laura's note and mug shot, take the
   wanted poster, and use the computer query.
5. Submit the transfer memo to Narcotics. Follow the homicide, fingerprint,
   and Chicago leads by telephone; the calls establish the Hoffman/Taselli/
   Pierson aliases and connect Taselli to Jessie Bains.

### Warrant, drug bust, and murder investigation

1. Use the emergency-number clue and case evidence to request a no-bail
   warrant from Judge Palmer. Take the issued warrant to the jail before the
   release sequence completes and hand it to the jailer.
2. Join the park drug operation. Observe the sale, question Victor Simms and
   the other students, ask the friend's name, question Colby about his source,
   and search the suspects. Arrest, read rights, handcuff, and search Sonny's
   assigned suspect, then book the arrested students and recover the cuffs.
3. Call Dispatch with the Colby/Pierson result. Speak with Sweet Cheeks in jail
   and obtain her agreement to help establish the hotel cover.
4. At Cotton Cove, inspect the body and clothing and call in the identification
   information. The body is Hoffman/Taselli, murdered execution-style. Read
   the Hoffman file and complete the computer and telephone research before
   proceeding to the undercover briefing.

### Undercover operation

1. Attend the full Narcotics briefing. Receive the white suit, trick cane,
   marked money, hair bleach, and planned transmitter. Shower, bleach Sonny's
   hair, change into the white suit, and leave uniform-only equipment secured
   at the station.
2. At Hotel Delphoria, register as **Jimmy Lee Banksten**, pay for the room,
   take the room key, and enter the assigned room. Contact Lieutenant Morgan,
   send Sweet Cheeks away by cab, and tell backup the later operation will be
   in **Room 404**. Meet the detectives and take the transmitter pen.
3. In the cocktail lounge, order the drink that signals Sweet Cheeks. Let her
   introduce `Whitey` to Woody. Use marked money to buy Woody's cooperation,
   then follow him into the back room.
4. Complete the preliminary poker sequence and retain the resulting invitation
   or password. Enter the high-stakes game, continue until the script identifies
   Jessie Bains, and preserve the transmitter and backup states.
5. Follow Bains to Room 404. During the confrontation, let the backup officers
   respond to the transmitted evidence and room location. The successful
   branch wounds and arrests Bains rather than killing Sonny.
6. Allow logic 103's trial and sentencing sequence to finish; its late four-
   point award precedes room 104. The parade and `You've won Police Quest!`
   message are the terminal checkpoint.

## Score Evidence

The following is an evidence ledger, not yet a claimed closed 245-point replay.
It prevents syntactic score sites from being mistaken for independent awards.

| Constraint | Raw points | Winning-route points | Reason |
| --- | ---: | ---: | --- |
| Helen proposition and citation conversation | 9 | 7 | The two one-point corrupt responses are outside the citation route |
| Gun-locker alternatives | 4 | 2 | Revolver and loaded-revolver parser branches share one guard |
| Station phone-number discovery | 4 | 2 | Examine-phone and ask-number branches share one guard |
| Drug-source questioning across logics 56/57 | 9 | 5 | Three parser paths share one information flag; choose the five-point branch |
| Newspaper availability in briefing rooms 44/45 | 2 | 1 | Both room versions share one availability flag |
| Room 404 notification | 7 | 5 | Early transmitter and late phone fallback share one guard |

These proved constraints remove 13 points from the raw 270. Further
phase-incompatible positive branches must remove 12 points to reach the
declared 245. Their exact grouping remains open because flattened condition
reports lose the distinction between sequential phases and mutually exclusive
room states. The next pass must follow the controlling phase variables through
logics 43--47, 56--60, 67--71, and 109, then validate score checkpoints in the
original interpreter. Until that is done, **257 is only a static upper bound,
not an asserted obtainable score**.

## Failure and Dead-End Map

- Missing or disrupting briefing can result in firing or administrative leave.
- Entering the shower clothed or leaving it running subtracts points.
- Mishandling a loaded revolver can shoot Sonny; carrying it into the jail
  lets prisoners seize it.
- Failing to search, restrain, or control suspects creates fatal attacks or
  invalid bookings.
- Accepting Helen's proposition abandons correct procedure.
- Missing the warrant timing permits Hoffman's release sequence to advance.
- Revealing the undercover identity, omitting backup, or entering Bains' room
  without the transmitter chain leads to failed or fatal confrontation paths.
- Leaving required evidence or equipment behind can create a late operational
  dead end even when the room graph remains navigable.

## Replay Work Remaining

1. Close the remaining 12-point reachability gap directly from phase-variable
   and room-entry control flow.
2. Record exact parser text for every route action, especially booking charges,
   warrant evidence, computer searches, hotel registration, and poker input.
3. Map deterministic movement coordinates and timing for patrol stops, the
   park bust, briefing animations, poker, and Bains' room.
4. Run the route under the original interpreter with score, room, inventory,
   and phase checkpoints, including a terminal 245/245 capture.
5. Package the resulting input stream and checkpoint manifest as a reusable
   whole-game conformance scenario.
