# StoreSignal AI - Screen Recording Script

Target length: 3:00. Record in one take. If you flub a line, pause 3 seconds,
restart that sentence - do not restart the recording.

## Pre-recording setup (do this BEFORE you hit record)

1. Reset and rebuild, so every number is fresh:
       make reset && make all && make eval

2. Launch the UI:
       make ui

3. In the browser, open the Local URL (usually http://localhost:8501 or :8503).
4. Set browser to full screen (Ctrl+Cmd+F).
5. Zoom the browser to 110% (Cmd + "+" once) so text is readable on video.
6. Close all other browser tabs, Slack, Mail, notifications.
7. Turn on Do Not Disturb (click clock in menu bar -> focus -> Do Not Disturb).
8. Open QuickTime -> File -> New Screen Recording.
9. Click the dropdown arrow next to the record button -> select your
   microphone (MacBook Microphone).
10. Do a 10-second test recording to check audio level. Play it back.
    If too quiet, move closer to the mic.

## Recording

### 0:00 - Hit Record. Wait 2 seconds of silence.

### 0:02 - Opening (voice over Command Center tab)

Say: "Retailers collect thousands of customer and employee messages across
four channels. The important signal - a broken freezer, a mislabelled
allergen - is fragmented, buried in noise, and surfaces weeks late."

Pause 1 second.

### 0:18 - Command Center

Action: The Command Center tab is already active. Move mouse to the four
metrics at the top (do not click).

Say: "StoreSignal AI processes forty thousand and thirty-one records from
reviews, in-app comments, staff shift notes, and call transcripts - in
English, Hinglish, transliterated Tamil and Marathi."

Action: Slowly scroll down to the priority queue table.

Say: "The priority queue ranks every alert by policy first, then rising
trend - never by volume alone."

Pause 1 second.

### 0:45 - Incident Explorer

Action: Click the "Incident Explorer" tab.

Action: In the Region dropdown, click and select "West".
Action: In the Category dropdown, click and select "refrigeration".
Action: Click the first incident card to expand it.

Say: "Here is one incident. These records arrived on different channels,
different days. The system fused them into a single incident and kept
every source snippet as evidence."

Pause 2 seconds while the card is open - let the viewer read.

### 1:15 - Early-Warning Radar

Action: Click the "Early-Warning Radar" tab.

Action: Store dropdown -> select "S014".
Action: Category dropdown -> select "refrigeration".

Say: "This is the killer feature. Small absolute volume, but rising sharply
at one store."

Action: Move mouse to point at the peak of the line chart.

Say: "A robust z-score against a rolling baseline flagged it twenty-four
days before the reference point - three and a half weeks of lead time
before this would have gone national."

Pause 1 second.

### 1:45 - Safety escalation

Action: Change Category dropdown to "allergen_risk".
Action: Change Store dropdown to "S007".

Say: "Now the safety layer. Only a handful of reports - volume alone would
never trigger an alert here."

Action: Move mouse to the flagged days table below the chart.

Say: "But allergen is a mandatory-risk category. Policy escalates it
regardless of volume, routed to Food Safety with a two-hour SLA."

Pause 1 second.

### 2:10 - Regional brief

Action: Click the "Regional Action Brief" tab.
Action: Region dropdown -> select "West".

Action: Slowly scroll through the brief as you speak.

Say: "Every week, one page per region. Top five incidents with evidence
quotes, owner, next step, and honest data caveats. No narrative - just
action."

### 2:35 - Proof

Action: Click the "Model & Trust" tab.

Action: Move mouse to the three metrics at the top.

Say: "Real measured numbers, not placeholders. Macro-F1 of zero point
six two six against hidden labels. Escalation precision of zero point
nine seven four."

Action: Move mouse to the seeded incidents table.

Say: "And all three seeded incidents detected, with lead times of seven,
twenty-four, and five days."

Pause 1 second.

### 2:55 - Close

Action: Do not move the mouse.

Say: "StoreSignal turns scattered store chatter into earlier, explainable,
accountable action."

### 3:00 - Stop recording.

## Post-recording

1. In QuickTime, File -> Save. Name it `storesignal_demo.mov`.
2. Play it back once end to end. Check:
   - Audio is clear throughout
   - No notifications popped up
   - No browser tabs visible that shouldn't be
   - The numbers you said out loud match what's on screen
3. If something is broken, re-record only that segment and splice in
   QuickTime, or just re-record the whole 3 minutes - it's short.
4. Export as MP4 if the submission portal requires it:
   File -> Export As -> 1080p.

## If you flub a line

Do not stop the recording. Just pause, take a breath, and repeat the
sentence from the beginning. You can trim the pause later, or just leave
it - judges forgive small stumbles. Restarting from scratch every time
takes 10x longer.

## If the UI is slow to load a tab

Wait silently. Do not say "um" or narrate the delay. The browser spinner
is fine on video.
