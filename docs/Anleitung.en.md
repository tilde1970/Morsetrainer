# Morsetrainer – Manual

A Morse code (CW) trainer for everyone from complete beginners to
contesters (people who take part in radio contests), developed by
**DL4YM**. A short overview with pictures is in the
[README](../README.en.md).

This manual is also in the program: F1 or the **Help (F1)** button at the
bottom right opens it at the section of the current tab, Ctrl+F searches
in it. With announcements on, the down arrow reads the next paragraph.
**Open online in browser** shows it in your browser (needs internet),
which a screen reader reads well. In the Contest tab F1 sends CQ; there
Ctrl+F1 opens the help.

**Language:** the program starts in German. Switch to English with
Ctrl+Comma (the button is called “Einstellungen … (Strg+,)”) → “Sprache /
Language”; it takes effect after a restart (“Jetzt neu starten” restarts
right away).

**Blind or visually impaired?** Section 8 “Accessibility” describes
announcements, keyboard operation, font size and contrast.

**Contents**

1. Getting started
2. Header and settings
3. The tabs: One by one, Non-stop, Speak, QSO, Contest, Statistics
   (Network is in section 7)
4. Daily practice
5. Awards and lifeline
6. Band conditions
7. Network: practising as a group
8. Accessibility
9. Keyboard shortcuts
10. Installing and updating (including “No sound?”)
11. Data

## 1. Getting started

The Morsetrainer follows the **Koch method**: you learn the characters at
full speed as a sound pattern from the start, first two, then one more at
a time. The default is **Koch speed 20/10**: the characters come at
20 WPM, with longer gaps between them. So you hear each character as a
whole instead of counting dits and dahs.

First turn the system volume down: the Morse tone has a fixed level and is
not quiet. If there is no sound at all, see “No sound?” in section 10.

1. Set **Koch lesson** at the top to 1 (K and M; already set on first
   start). “▶ listen” plays the new character.
2. In the **One by one** tab choose **Content** “Characters” and practise.
   The **time limit** is on: there is no time to count, the character has
   to come as a sound pattern. After a run with at least 50 characters and
   90 % correct, the program suggests groups.
3. Choose **Groups** and copy while the audio plays. With at least 50
   characters and 90 % on the first attempt, the program offers the **next
   lesson** (details under “Koch lesson and moving up” in the One by one
   tab).
4. From lesson 6 there are enough **words**; then come Non-stop and QSO
   (see “Your learning path”).

**Or** press **▶ Daily practice (10 min, F12)**: it puts together what is
due every day and switches the tabs by itself (section 4). **Do you
already know CW?** Switch on **Returning to CW** under “▸ More options”
(section 4).

Short and daily beats long and rare: the footer shows today's practice
time and the daily goal, the week strip at the top the days you practised.

### Your learning path

A suggestion for how to get from the first characters to operating on the
air. The times are rough ranges for 10–20 minutes of practice a day. The
awards (section 5) are milestones, not requirements. Daily practice leads
you through steps 1 to 3 and then the speed; anything beyond that you
choose yourself.

1. **Lessons 1–9** (about 2–4 weeks): recognise characters instantly as a
   sound pattern, first with time limit, then in groups. Milestone: Koch
   Bronze with lesson 10.
2. **Lessons 10–29** (about 2–3 months): hear words as a whole. On your
   own: Words with “Listen first”, abbreviations and plain words, from
   lesson 25 phrases, Speak. Milestones: Koch Silver with lesson 25,
   Copying in flow from lesson 15.
3. **Lessons 30–41** (about 1.5–2.5 months): the full character set with
   digits, punctuation and callsigns. On your own: RufZ runs. Milestones:
   All digits, Koch Gold with lesson 41.
4. **Lessons 42–45** (a few days): the prosigns AR, KN, SK and BK, which
   occur in QSOs. You set the lesson yourself (see “Koch lesson and moving
   up”).

From here the steps run side by side, each over weeks to months:

5. **Speed and plain text in flow:** daily practice first shortens the
   Farnsworth gaps, then makes the characters faster. On your own:
   Non-stop with plain text, phrases or QSO plain text. Milestones:
   Copying in flow, QRQ.
6. **Callsigns as in a contest:** RufZ runs without prefix filter.
   Milestones: Rufz, WPX.
7. **Understanding QSOs:** in the QSO tab first “log check” with a short
   length, then “head copy + questions”. Milestones: First QSO understood,
   Headphones.
8. **Contest and pile-up:** in the QSO tab as a contest run, first
   without, then with pile-up, then as the run station in the Contest tab.
   Milestones: Contest, Worked All Contests.
9. **Under band conditions:** once a character set sits firmly without
   interference (90 % or more), start with “light” (section 6).
   Milestone: QRN-proof.

## 2. Header and settings

### Header

The bar at the top above the tabs applies to all tabs. It has no heading
of its own. It holds the Koch lesson, the speed in WPM (words per minute,
default 20), the pitch (default 600 Hz) and, in the “Characters” field,
the character set. On the right is the speed in characters per minute,
with Farnsworth the effective speed (“≈ 50 CPM effective” at 20/10).
**▸ More options** holds the practice options:

- **Farnsworth:** characters at the set speed, but longer gaps between
  them (Koch speed 20/10). Below 18 WPM character speed you can count the
  dits and dahs; the header points this out and offers Koch speed.
- **Favour weak characters:** characters you often confuse or recognise
  slowly, and those due today in the review box, come more often. The last
  14 days count most.
- **Vary pitch and speed slightly:** if you only ever hear one sound, you
  will find it harder on the band.
- **Returning to CW:** for everyone who used to know CW. Daily practice
  moves up faster (from 95 % on the first try by three lessons, from 85 %
  by one) and, if no speed is saved yet, starts at 15 WPM without
  Farnsworth. You can untick the box at any time.
- **Band conditions:** set up the interference (section 6).

### Settings

**Settings … (Ctrl+Comma)** opens a window with everything you set once:

- **Station:** callsign and name appear on the awards and are the default
  for “My callsign” in Contest and “Name/callsign” in Network. Without a
  callsign of your own the name is enough; for the contest you then enter
  a made-up callsign. The optional **locator** (Maidenhead, four or six
  characters, e.g. `JO41`) decides where the generated stations in QSO and
  Contest come from; without a locator the country of your callsign
  counts. An invalid locator is named below the field.
- **Practice:** the daily goal in minutes (default 10, 0 = no goal).
  **Relaxed daily practice** takes the time limit out of the warm-up, for
  everyone who needs more than 1.5 seconds per answer. These warm-up
  blocks do not count for the review box and the awards that depend on it
  (Worked All Letters, All digits).
- **Sprache / Language:** switch the interface to English. It takes effect
  after a restart (**Restart now** at the bottom of the window). The voice
  in the Speak tab stays German.
- **Accessibility:** font size, high contrast, announcements (section 8).
- **Data:** back up, restore, open the data folder (section 11).

**Font size:** in the settings or with Ctrl+Plus, Ctrl+Minus and Ctrl+0
(normal) the whole interface gets larger, up to 200 %, or smaller, down to
75 %. The window grows with it; the setting is saved.

**Compact header:** at 200 %, and earlier if the window would otherwise be
taller than the screen, the header is collapsed to one line, such as “▸
Koch lesson 3 · 20/10 WPM · 600 Hz · KMUR”. The line is a button: click
it or press Enter or the space bar to open and close the header; the
announcement says “Header expanded.” or “Header collapsed.” “Settings …”
stays on the right of the line. At 200 % the week strip appears in the
Statistics tab under “This week”.

## 3. The tabs

The tabs are **One by one**, **Non-stop**, **Speak**, **QSO**,
**Contest**, **Network** and **Statistics** (Alt+1 to Alt+7). Start and
stop with the button or F5 (F10 in Contest).

### One by one

Listen, answer, the next one. Under **Content** you choose
**Characters**, **Groups**, **Words** or **Callsigns** (with the arrow
keys, or press Alt+1 again); the choice is saved. F5 or the **Start (F5)**
button starts and stops, Esc stops too. The space bar repeats; a
character recognised only after the repeat counts as not recognised.
After stopping, the status line shows the result, e.g. “Run finished: 46
of 50 characters correct (92 %).” The options for the exercise are above
the Start button and are hidden during a run in Groups, Words and
Callsigns.

**Characters:** recognise single characters, without interference. After
each answer you see your reaction time and the limit, e.g. “0.38 s, limit
1.20 s”.

- **Time limit** (Instant Character Recognition): it counts from the end
  of the last dot or dash, starts at 2 s and moves between 0.5 and 3 s:
  shorter while you answer reliably, longer when you miss characters.
  “reset” sets it back to 2 s. F11 (“Where am I?”) pauses the time limit
  while a character is waiting for your answer; the character then does
  not count and comes again later.
- **Feedback beep:** a high beep for a correct answer, a low double tone
  for a wrong one (default off).
- After a confusion you hear the correct character and the one you typed
  one after the other. The wrong character is played again right away and
  once more after four to eight others; these repeats count within the
  run, but not for the overall statistics, the review box and the
  weighting.

**Groups:** copy groups of characters. The group length can grow: one
longer after 5 correct groups, one shorter after 2 wrong groups (each on
the first attempt). After an error you see and hear the solution, then it
goes on as on the air.

**Words:** CW abbreviations, Q codes and QSO words, only from characters
you already know. The default is “Listen first”: hear the whole word,
then type. The meaning is shown after the answer. You can add your own
words (section 11). Under **Type** you choose what comes:

- **Abbreviations:** abbreviations, Q codes and some words written out.
- **Plain words:** about 300 English words written out, as they occur in
  QSOs (WEATHER, STATION, THANKS …), without meanings, from lesson 10.
- **Phrases:** whole pieces of QSOs such as “TNX FER CALL” or “UR RST
  599”, from lesson 25. You type them without spaces; after the tone you
  have 2 s to start, then 0.6 s per character.
- **mixed:** abbreviations and roughly every third sequence a phrase.

**Callsigns:** real callsigns from the Super Check Partial list, by default
only from characters you have already learned (from Koch lesson 23 with
the first digit), occasionally with /P, /M, OE/… as in contests. If there
are too few real callsigns (under 30, under 50 for a RufZ run), the
trainer makes up matching ones from patterns; the line above the load
button says so. Optionally as a **RufZ run** (modelled on RufzXP): 50
callsigns, one attempt each, the speed grows, score = length × effective
speed. Afterwards you can replay the missed and slowly recognised
callsigns (F6).

**Loading the callsign list:** the **Load callsign list
(supercheckpartial.com)** button downloads the list from
[supercheckpartial.com](https://www.supercheckpartial.com) (about 360 kB,
needs internet); afterwards it is called **update list**. During an
exercise it does not load. If loading fails, the previous list stays, and
the status line and the announcement give the reason, such as “No
connection to supercheckpartial.com (internet or proxy).” Behind a company
or school proxy, download `MASTER.SCP` in your browser, rename it to
`callsigns.scp` and put it in the data folder (section 11); it applies
after a restart.

**Options in Groups, Words and Callsigns:**

- **Group length from … to** (Groups only, default 2 to 5) and **Length
  adapts** (default on).
- **Input:** *Copy while listening* (type while the audio plays), *Listen
  first* (type after the audio) or *Head copy* (type nothing; Enter
  reveals, then J = knew it, N = didn't). Head copy relies on your own
  assessment and does not count for the overall statistics and the lesson.
- **Speed adapts** (as in RufzXP): correct on the first attempt +1 WPM,
  wrong −1 WPM (effective speed). With Farnsworth the gaps get shorter
  first, then the characters get faster. The characters get slower only
  down to 18 WPM, below that the gaps get longer. The same rule applies to
  “Adjust speed automatically” in the QSO tab.
- **Show solution after** 1 to 3 failed attempts (default 1). In Groups,
  with more than one attempt only the wrong positions are marked at first.
- **Band conditions** on and off (section 6).
- **Duration** of the run in minutes (default 5, 0 = no limit) and
  **Feedback beep**.

**Koch lesson and moving up:** if you get 90 % on the first attempt in a
run of at least 50 characters in Groups or Non-stop, the next lesson is
offered.

- A first attempt only counts without repeating with the space bar and
  with a quick answer (1.5 s plus 0.6 s per character after the end of the
  tone); typing too much counts as an error.
- Weak and new characters automatically come up more often.
- **Lesson 41** completes the 40 lessons of lcwo.net: all characters,
  none favoured as new any more. Next to the Lesson field it says “all
  characters · prosigns from lesson 42”.
- In **lessons 42–45** the prosigns from QSOs are added: AR (key `+`), KN
  (`(`), SK (`*`) and BK (`#`). The program does not move there by itself:
  you set the lesson at the top (the evening summary of daily practice
  points this out once, with a **Set lesson 42** button). After that the
  next prosign is offered again. Daily practice also repeats prosigns you
  have learned.

### Non-stop

The audio keeps running without waiting, you type along; even if you fall
behind, it carries on. Under **Content** you choose **Random characters**
(in groups, default 5, with a word gap; continuous with group length 0) or
plain text: **Abbreviations**, **Plain words**, **Phrases**,
**Callsigns**, **Numbers** or **QSO plain text** (complete QSOs).
**Numbers** mixes what turns up as a number on the air: signal reports
(599), CQ zones, serial numbers, frequencies, power, times, years and
short numbers as in contests (5NN for 599, T for 0: TT7 = 007), only from
the digits you have learned (at least four). Plain text and numbers do not
count for the lesson. Optionally band conditions run under the whole run.

- A key only counts if it fits the character: not guessed in advance and
  at most 5 s after it; typing too much counts as an error.
- After stopping (F5 or Esc) a comparison shows the last 90 characters.
- **Everything in a separate window** shows the whole run, errors in red
  and marked with ^, optionally only the sent text, to check against your
  paper; the font size can be changed and the text copied.

### Speak

Listen and say without a keyboard (like Morse Code Ninja): Morse code,
then a thinking pause in which you say out loud what you heard, then a
voice announces the solution and the code comes once more.

- **Content** (at the top): characters, groups (adjustable length, default
  5), abbreviations, plain words, phrases, callsigns. **Count** of items:
  default 50.
- Characters, groups and callsigns are spelled in the phonetic alphabet
  (Alfa, Bravo …), words and phrases as a whole or with their meaning.
- The thinking pause is deliberately short (default 1 s plus 0.3 s per
  character).
- Switches (all on by default): **Announce words and phrases as a whole**,
  **Add the meaning when spelling** and **Send the Morse code again
  afterwards**. **Save as MP3** exports for on the go.
- Counts only for practice time. The voice is always German.

### QSO

Listen to complete QSOs (radio contacts): normal QSO or contest runs (CQ
WW, CQ WPX, WAG, ARRL DX, IARU HF) with adjustable pile-ups (many callers
at once, default off). Next to the length the estimated duration is shown.
Evaluation is your choice:

- **log check**: log afterwards, F8 checks;
- **typing along**: continuously as in Non-stop, result in percent;
- **head copy + questions**: no notes, afterwards questions about name,
  QTH, rig, weather … or the exchange;
- or listen only.

How often you used “Again” before checking is noted. “Adjust speed
automatically” follows the same rule as “Speed adapts” in One by one. The
zones in the exchange (CQ WW, IARU HF) follow the digit of the callsign
and are therefore rounded for large countries such as the USA, Canada and
Russia.

Stations with /P or /M after the callsign only occur once the slash is
among your learned characters. Once D, U and P are learned, a station that
is already in the log occasionally calls again in a contest run; the
running station says “DUP”, and that is not a new QSO.

### Contest

You are the running station (similar to Morse Runner): call CQ, pick up
callers, send the exchange, log. F10 starts and ends. The function keys
are laid out as in contest programs (section 9).

- As in a real contest, callers sometimes answer to an almost correct
  call. If you notice the mistake, correct the call and confirm with Enter
  (“Call TU”), otherwise “Busted” appears in the log.
- “?” in the call field asks back (DL1?, DL?ABC).
- Speed and pitch spread of the callers are adjustable.
- At the end there is a summary by type of error.

### Statistics

Overall statistics per character, only from random characters and
callsigns, because in words, phrases and QSOs the context gives away too
many characters. Runs with band conditions do not count here (section 6).
The tab is long; the “Jump to” buttons at the top lead to week, awards,
lifeline, review box, confusions, insights and progress. F11 reads out an
overview.

- **Comparison:** below the total you see how the last 7 days went
  against the 30 days before, e.g. “Before (30 days): reaction 0.61 s, 88 %
  correct (from 412 characters) · Last 7 days: reaction 0.48 s, 92 %
  correct (from 96 characters)”; for the reaction, smaller is faster. A
  period appears from 10 characters. Here you see whether you are getting
  better; the averages over all runs hardly move, because the early, slow
  answers always count. New characters slow the average down at first and
  are listed at the end as “New”. If you practised more than one mode,
  “By mode: One by one 81 % → 81 %, Non-stop 78 % → 87 % …” follows
  (accuracy before → now).
- **Characters sorted by error rate:** the character with the highest
  error rate is on top. The column “Confused with” lists the characters
  you typed instead of the one sent (“6 (2)”) and the other errors: “too
  slow”, “only after repeating”, “missed” or “swapped”. Above the table you
  see which characters are solid (box 3 of the review box or higher).
- **This week:** the week strip with stars and the weekly goal.
- **before → now (s):** the reaction per character as a median (“0.80 →
  0.45”), last 7 days against the 30 before, from 20 measurements on each
  side.
- **Ø reaction:** the time from the last dot or dash to your input,
  averaged over the correct answers. A reaction under about 0.6 s is a
  common guide for recognising without thinking.
- **Ø WPM:** the effective speed of the correct answers.
- **Review box** (spaced repetition over days): characters recognised
  reliably and quickly come back after 1, 2, 4 … 32 days (box 1 to 6),
  uncertain ones the next day. Decided once a day from 8 attempts. Due
  characters come up more often with “Favour weak characters”; below, each
  box lists the characters in it.
- **Most frequent confusions** of the last 30 days, with a button to
  practise them. A pair is listed from 3 cases; pairs that do not sound
  alike (such as E and 7) are marked “typo?” and stay out of the practice.
  The button switches to One by one and sets the character set to these
  characters for the run and switches on “Favour weak characters”;
  afterwards your own character set is back. If
  there are too few confusions yet, below the list it says “Not enough
  confusions yet for targeted practice.”
- **Insights (last 90 days):** the **Read the insights aloud** button and
  F11 read out all lines. Each line says what is still missing; at the
  start several are empty. They are: **Lag when copying** (how far you
  trail behind the tone in Non-stop), **Error types per week** (the
  **Practise unrecognised characters** button practises the unrecognised
  ones), **Fatigue within a run** (accuracy in the first, middle and last
  third of long runs), **Confusion pairs over time** (the **Practise these
  characters** button practises these pairs), **Characters over time**
  (error rate per character, last 14 days against before) and **Shaky
  again** (characters that have fallen back at least two boxes in the
  review box).
- **Awards** and **lifeline** (section 5) and the **progress history** per
  exercise (runs with fewer than 5 characters are left out there).

## 4. Daily practice

Can't be bothered to decide what to practise today? **▶ Daily practice
(10 min, F12)** at the top puts together ten minutes from whatever is due
and switches the tabs by itself. Afterwards the tab settings are back as
they were. Warm-up, main part and wind-down depend on your level:

- **Lessons 1–9:** warm-up with characters and time limit (3–4 min), main
  part groups at a fixed speed, wind-down Non-stop with groups of 3 (2
  min).
- **Lessons 10–29:** as above, the wind-down is words (2 min).
- **Lessons 30–41:** as above, the wind-down is words (mixed with phrases
  from lesson 35) or callsigns, alternating from one practice day to the
  next (2 min).
- **After Koch (lesson 41 passed):** warm-up with characters (2 min), main
  part Non-stop with groups of 5 (4 min), wind-down (4 min) in turn:
  callsigns, QSO for head copy, callsigns, contest run with log or band
  conditions.

The parts in detail:

- **Warm-up:** all characters of the lesson; those due today in the review
  box come more often, or, if nothing is due, your most frequent
  confusions. With many due characters it takes up to 4 minutes, because
  each needs eight attempts for the review box to decide it today. The
  time limit continues where it ended last time and is never longer than
  1.5 s here. If you need longer, switch on **Relaxed daily practice** in
  the settings.
- **Speed:** the main part keeps a fixed speed (characters at least
  18 WPM). It changes once a day, effective from the next: below 75 % on
  the first try (at least 100 characters) 1 WPM slower. After Koch, 90 % or
  more also makes it 1 WPM faster. Before that only the pauses get shorter
  (effective speed 1 WPM faster), from 95 % on a day without a lesson step,
  not in the first days of a new lesson.
- **Lesson:** if the main part meets the Koch criterion (50 characters,
  90 % on the first try), the next lesson applies from the next day, no
  question asked. Daily practice keeps its own lesson for this (the first
  time the one from the header); lesson and character set at the top stay
  as you set them for free practice. On the first day of a new lesson a
  card shows the new character and plays it.
- **Do you already know CW?** Switch on **Returning to CW** (header, “▸ More
  options”). As a contester, set lesson 42 and your speed at the top
  before the first time; daily practice takes both over.
- **Wind-down after Koch:** the **QSO for head copy** (short, “head copy +
  questions”) only comes once you have learned AR, KN, SK and BK and it
  fits into the four minutes at today's speed, questions included,
  roughly from 18 WPM effective; otherwise you get callsigns. The block
  ends with “Check” (F8); there is no “Again” here. The **contest run**
  (short, no pile-up, changing contests) is logged as you listen. From
  15 WPM effective, every second contest slot brings **Non-stop under band
  conditions** instead (groups of 5): first “light”, after two days with
  90 % or more “medium”; twice in a row below 80 % takes you back to
  “light”. Each day the first complete run counts; if you make the band
  easier during a run, it does not count towards moving up. The level
  changes on the following day, and the evening summary tells you. The
  wide filter is used without strength differences and with the noise
  volume at 100 %; afterwards your own band settings are back. The results
  of these blocks do not count for stars, speed or lesson, but for the
  awards as usual (such as Headphones Bronze).
- **Three stars a day:** ★ *Showed up* for the full 10 minutes, ★ *Clean*
  for 90 % on the first try in the main part (80 % in the first three days
  of a new lesson), ★ *Ahead* for real progress: next lesson earned, a
  character reaching box 3 of the review box for the first time, a daily
  speed you never had before, or band “medium” in the wind-down for the
  first time. A second daily practice on the same day can add missing
  stars; earned stars are never lost, not even when you stop early.
- **Between the blocks** a card shows the result, new stars and what comes
  next. With at least 4 mistakes and at least 5 % of the answers it also
  says what caused them (“Of 9 mistakes, 5 were mix-ups, 3 too slow, 1
  missed”). The card stays until you continue with Enter or “Continue”.
- **Ending:** with the **End daily practice (Esc)** button. Esc and F5 only
  end it on the second press within three seconds (“Press Esc again to end
  the daily practice.”), and so do Ctrl+Q (Mac: Cmd+Q) and the window's
  close button. So a slip doesn't cost you the day.
- **Evening summary:** stars and where you stand on the weekly goal, what
  improved compared with the week before (only with enough data, never
  “worse”), how much is missing for the next lesson and tomorrow's speed
  with the reason. If the main part went well, you get **5 more min** once
  a day with something different: your confusions within the lesson, a RufZ
  run or words. After lesson 41 it points out the prosigns once; **Set
  lesson 42** sets them at the top.
- **After a break** of at least 14 days the bar welcomes you back. Stars and
  numbers stay; the speed adjusts.
- **Week:** next to the button is the week strip from Monday, e.g. “Mon
  ★★★  Tue ★★  Wed ✓  Thu –  Fri ·” (✓ = practised freely without daily
  practice, daily goal reached; – = no practice), and next to it where you
  stand on the **weekly goal of 8 stars**, e.g. “5 ★ this week, goal 8”.
  Five days of practice with one to two stars each get you there. The goal
  is not a limit: up to three stars a day keep counting, all together for
  the **Finest hours** award (section 5).

## 5. Awards and lifeline

### Awards

Like DXCC or WAC on the air: awards for what you can do for good, in the
levels **Bronze, Silver, Gold** and some in **Platinum**. They are checked
after every exercise. A new seal shows a window with the date and a
**Print** button; the award opens as a certificate in the browser (A4
landscape) with your callsign and name from the settings (which you can
also change in the window). During daily practice the window comes only
after the evening summary, which also mentions the new seals.

Every award has its own motif on the left in the style of an intaglio
engraving like on banknotes, and on the right the club house of the
Gütersloh amateur radio club (N47), where the Morsetrainer is made. With
a callsign entered, a unique number such as `DL1ABC-KOCH-G-20261004`
appears at the top right: callsign, award, level (B, S, G, P) and date.

<img src="bilder/diplom.en.png" width="640" alt="Example: Koch award in gold for DL1ABC">

**Overview:** in the **Statistics** tab under “Awards”, with the seals
achieved, the next goal (e.g. “Silver: 18 / 25 lessons”) and from which
lesson it can be reached. A selected row shows the condition and the state
of each level; announcements read out the condition. “View and print
award” shows the award of the highest level, “Preview: next goal” that of
the next open level, stamped “PREVIEW”.

The levels at a glance (the number after “from” is the lesson from which
the award can be reached). The exact condition is shown by the selected
row in the overview; “characters ≥ 18 WPM” means the characters must be
sent at 18 WPM or faster.

- **Koch** (from 1): lesson 10 / 25 / 41 passed, with ≥ 50 characters and
  ≥ 90 % on the first attempt (Groups or Non-stop).
- **Worked All Letters** (from 1): 10 / all 26 letters in box 3 of the
  review box; Gold: all in box 6 and all digits in box 4.
- **Copying in flow** (from 15): 10 / 15 / 22 WPM effective, in Non-stop
  with plain text (Gold only phrases or QSO), full 3-min run, ≥ 90 % minus
  extra keys.
- **QRQ** (from 40): 20 / 25 / 30 / 35 WPM, in Non-stop with random groups
  from the full character set, no Farnsworth, full 3-min run, ≥ 90 %.
- **High-Speed** (from 40): 25 / 30 / 35 / 40 WPM, in Non-stop with
  phrases or QSO plain text, otherwise like QRQ.
- **QRN-proof** (from 25): conditions light 90 % / medium 90 % / heavy
  85 %, in Groups or Non-stop with random characters, ≥ 200 characters,
  band conditions on for the whole run and not made easier, noise volume
  ≥ 100 %.
- **Rufz** (from 27): 2,000 / 3,500 / 5,500 / 7,500 points in a full run
  without prefix filter, starting speed ≥ 20 WPM.
- **Contest** (from 41): Bronze ≥ 20 WPM, Silver ≥ 25 WPM, Gold ≥ 30 WPM,
  with more QSOs and fewer errors at each level; run ≥ 10 min.
- **WPX** (from 25): 100 / 400 / 1,200 / 2,000 different prefixes, right at
  the first attempt.
- **Headphones** (from 41): 15 / 20 / 25 WPM effective, 3 normal QSOs in a
  row with “Head copy + questions”, all questions right, without “Again”.
- **Confusion overcome** (from 5): 1 / 3 / 6 pairs from your most frequent
  confusions, confused at most once in 28 days.
- **Endurance:** 10 / 50 / 150 / 365 days with ≥ 10 min of practice, not in
  a row.
- **Finest hours:** 50 / 200 / 500 / 1,000 daily practice stars.
- **Characters heard:** 5,000 / 25,000 / 100,000 / 250,000 correctly
  recognised random characters.
- **Club night:** 1 / 5 / 15 / 40 evenings with ≥ 10 min of network
  sessions in total with participants. This award only works together in
  the network and is listed last while it has no seal.
- Without levels: **First QSO understood** (from 40), **Worked All
  Contests** (from 41, all 5 contest types), **Q-code expert** (from 40,
  all 20 Q codes) and **All digits** (from 39).

General rules:

- For Koch, flow, QRQ, high speed, QRN-proof, Rufz and contest, **Silver and
  above need two different days**. Starting straight at lesson 41 gives
  Bronze on the first day and Silver and Gold with another passed run on a
  different day.
- Only runs without self-assessment count. RufZ runs with made-up
  callsigns count too.
- Seals achieved are kept with their date in the database and are never
  lost, not even with “Reset overall statistics”.

### Lifeline

Below the awards on the Statistics tab, the **lifeline** shows the long
road from your first practice until today: daily practice stars added up,
the highest Koch lesson practised (up to 41) and the daily speed, with the
award seals underneath as diamonds in their colour. All three lines only
rise or stay level, and they stay complete after “Reset overall
statistics”. Hover with the mouse to see the values and seals of each day.
Without a mouse, Tab into the lifeline; the left and right arrows move one
day, Page up and Page down one week, Home and End to the first or last
day, and announcements read out the values.

## 6. Band conditions

### Setting them

They are set in one place: **More options → Band conditions → Adjust …**,
“Adjust …” in a tab, or Ctrl+B. In the tabs you only switch them on or
off.

Each can be switched on and adjusted: band noise, static crashes (QRN),
QSB (fading), chirp (chirpy transmitter), SSB QRM (detuned speech), CW QRM
on the adjacent frequency and **strength differences** (how differently
loud the stations arrive in QSO and contest); plus the **noise volume**
relative to the signals. The buttons **light**, **medium** and **heavy**
set the levels that the QRN-proof award counts; the window shows which
level the setting matches at least:

- **light:** noise +8 dB (S/N), QSB 30 %.
- **medium:** +2 dB, QSB 50 %, QRN 30 %.
- **heavy:** −4 dB, QSB 80 % (dips down to −40 dB), QRN 50 %, CW QRM 30 %.

From “medium” to “heavy” is the biggest step: at “heavy” whole characters
go under in dips. Whether a dip hits a character is chance; if the
QRN-proof award does not work out at once, a second run is worth it.

- **Signal-to-noise ratio (S/N):** the slider ranges from +20 dB to
  −10 dB, measured in the receiver filter (300–2700 Hz). The ear hears CW
  like a filter of about 50 Hz, where the ratio is roughly 16 dB better,
  so −4 dB feels like about +12 dB. As with a receiver with AGC, the noise
  gets louder between characters (at most 12 dB); during the tone the set
  ratio applies. If you change the pitch, choose the level again.
- **Fading** is random as on the band: mostly shallow, now and then a
  deeper dip. The higher the slider, the more often and deeper.
- **Chirp** is shown in Hz (largest offset while keying).
- **CW QRM offset:** the adjacent run is **far** (300–500 Hz) away,
  **close** (50–200 Hz) or at **zero beat** (almost on your frequency).
  Close and zero beat train the selective listening that contesters need.

**More interference** (expandable) is not part of any level and does not
count for the award; “All on” does not switch it on: thunderstorm, AGC
pumping, flutter fading (aurora), carrier (someone tuning up), switching
power supply, PLC (powerline data noise), electric fence and key clicks.

**CW filter:** 2.4 kHz (like an SSB filter, the default), 500 Hz or 250 Hz
around your pitch. A narrow filter removes noise (500 Hz about 6 dB,
250 Hz about 9 dB) and QRM that is far away. It does not help against
close or zero-beat QRM, it rings slightly, and stations off your pitch get
quieter. The whole picture gets quieter; raise the volume in the band
window if needed. The levels and the award count the S/N value inside the
filter, which the window shows in addition: “medium” with a 500 Hz filter
is about “light”.

**Listen (Ctrl+P)** (button at the bottom of the window): plays CQ calls
at your pitch and speed under the conditions currently set, with your
callsign, without a time limit. Whatever you change meanwhile can be heard
at once; a second press stops. It counts for nothing. During a run and in
a network session the button is disabled.

### Practising with band conditions

**When to switch on?** Learn new characters without interference; that is
why Characters in the One by one tab has none. Band conditions pay off
once the character set is solid without them (90 % or more); then start
with “light”. Practice works best at “light” to “medium”; “heavy” is for
polishing.

- **During a run:** strength and volume take effect immediately; the
  award then counts the weakest setting of the run. In Groups, Words,
  Callsigns, Non-stop and Network you can switch them on or off only
  between runs, in QSO and Contest at any time.
- **In the answer pause** fading, noise and neighbouring QRM keep running
  as on the air. If you need silence there (with tinnitus, for example),
  switch off “Band in the answer pause” in the window; it makes no
  difference to the level or the award.
- **The solution** after too many failed attempts always comes without
  interference.
- **Statistics:** runs with band conditions appear in the history but do
  not count for the character statistics, the weighting, the confusions or
  the review box: a character lost in the noise says nothing about whether
  you know it.
- **On the network** all participants hear the trainer's setting, with the
  same fading, the same stations and the same neighbouring QRM. Only
  someone with their own `callsigns.scp` may hear other callsigns in the
  QRM.

## 7. Network: practising as a group

For classes and club evenings: all computers are on the same network
(Wi-Fi or LAN), one is the **trainer**, the others join as
**participants**. Only text is sent; each computer generates the sound
itself, with no dropouts, with its own headphones and its own pitch. Read
“Connection and security” at the end of this section first.

### Trainer: leading a session

1. In the **Network** tab choose “Trainer” and **Open session**. The
   program shows the address and a four-digit PIN for the participants.
2. Choose the **content**: characters, groups, abbreviations, plain words,
   callsigns, phrases, QSO plain text or **own text** (one line per
   sequence; prosigns as + for AR, ( for KN, * for SK, # for BK).
3. Choose the **number of sequences** (for QSO plain text whole QSOs, sent
   in sections up to the next =, K or closing sign), the **answer time**
   and band conditions. Character set, speed and Farnsworth come from the
   header.
4. Press **Start**. First comes the start sign VVV = (can be switched
   off), after the last sequence the end sign +. Everyone gets the same
   sequence at the same time. The next one comes once everyone has answered
   or the answer time is up, or with **Next** (F7). **Repeat for everyone**
   (F6) plays the current one again.

**The table** shows each participant's current answer, share of correct
characters, how many sequences were **fluently** correct and typical time
from the end of the tone to Enter, and below it the group: accuracy, share
of fluent sequences, most common errors, weakest characters.

- **Fluent** means correct on the first hearing and fast enough that
  nobody counted (1.5 s plus 0.6 s per character after the tone, as for
  Groups in the One by one tab). The answer time is only the hard limit.
- Clicking a participant shows their errors and weakest characters.
- With many participants the table can be moved **into a separate window**
  (for a second screen or a projector); F5–F7 work there too.
- **Speed recommendation:** after enough sequences at the same speed (50
  characters across everyone), faster from 90 % fluent, slower below 75 %,
  applied with a button in steps of 1 WPM effective.
- **Save as CSV** stores a table in `stats/` (results per participant, one
  column per sequence with what was typed and the time).
- **Solutions:** the button next to it opens a window for the projector.
  During the run it shows the current number in large type, afterwards all
  solutions numbered; ↻ marks what was repeated for everyone. A−/A+ change
  the font size, **Copy** puts the list on the clipboard. Clicking a
  solution plays it again on the trainer's computer.

### Flows

**Wait for answers** (default): as described above.

**Fixed pace (copying on paper):** for classes where not everyone has a
computer. The next sequence comes after the tone plus a **writing pause**,
whoever has answered.

- The pause is the same for every sequence; its default depends on the
  content (characters 2 s, abbreviations and plain words 3 s, groups,
  callsigns and own text 4 s, phrases and QSO 5 s).
- Until the end the trainer's screen shows no solution (it may be on the
  projector), only “No. 7 of 20”.
- **Repeat for everyone** (F6) extends the deadline, **Next** (F7) moves on
  at once. Blocks of 20–25 sequences with solutions in between work better
  than “until Stop”.
- **Pen and paper only:** needs neither a computer nor a login but listens
  through the trainer's speakers, so switching to the fixed pace turns on
  “Also play on this computer”. Participants check their own copy against
  the solutions or hand in their sheet; after the run the trainer types it
  in under **Enter paper sheet** (name, then the line for each number,
  empty = missed).
- **With a computer, but on paper:** anyone who still wants to copy with a
  pen ticks “With fixed pace, copy on paper and type it in at the end” when
  connecting. Afterwards there is one field per number to type in the copy,
  and **Evaluate** sends it to the trainer.
- Typed-in answers count for right/wrong, errors and weak characters, but
  without timing: not as fluent and not for the speed recommendation. The
  table shows “Paper” for them.
- **Print answer sheet** opens a sheet with numbered lines in the browser
  for printing.

**Non-stop:** under *Flow* choose “Non-stop” and set the **duration** in
minutes. Groups (or words, callsigns …) then come without pauses as in the
Non-stop tab until the time is up; everyone types along continuously,
without Enter. Scoring happens at the end as there. During the run the
trainer screen shows only the remaining time. Band conditions lie under the
whole run; own text is not available here.

**Sound for everyone from the speakers:** with “Sound for everyone only
from this computer (speakers)” only the trainer's computer plays; the
participants' computers stay silent and are only used for typing. Nobody
needs headphones and everyone hears the same thing at the same time. This
works in all flows and suits the fixed pace when paper and computers are
mixed.

### Participant: joining in

1. In the **Network** tab choose “Participant” and enter name or callsign
   and the PIN.
2. Choose **Search** (or enter the trainer's address) and **Connect**.
3. Type while the tone is still running. The answer is done with the last
   character; Enter is only needed if you have fewer characters.

- There is one attempt per sequence, then the solution is shown. If it was
  not fluently correct, the sequence is played again with the solution (the
  trainer can switch this off). If you are not finished in time, what you
  have typed so far is scored.
- At a fixed pace it then only shows “No. 7 noted”; the solutions come at
  the end as a list, and each sequence can be heard again with a
  double-click or space.
- The results count for your own statistics like a normal run.
- **Protect your hearing:** anyone with tinnitus or a hearing aid ticks
  “Interference quieter for me” and chooses 10–90 % of the trainer's
  setting. Only noise and interference get quieter, the signals stay the
  same; it can never be louder than at the trainer. The trainer sees a
  **↓** after the status and in the CSV file. When the trainer's
  loudspeaker plays, the trainer's setting applies.
- If the trainer has a newer program version, the participant is asked on
  connecting whether to download it (section 10); the Morsetrainer then
  restarts and connects again.

### Connection and security

- The trainer needs port 7373 (TCP) and 7374 (UDP) for the search. On
  Windows the firewall asks the first time: allow it for private networks.
  If the search finds nothing (some Wi-Fi networks block broadcasts), enter
  the address shown by hand.
- The connection is not encrypted, and the four-digit PIN only prevents
  mistakes, not attackers. Anyone reading along on the same network sees
  names, practice text and answers and could log in with the PIN. Network
  mode is meant for a club or home network; on unfamiliar or public Wi-Fi
  (hotel, café, fair) better not open a session, and close the session
  after the class.
- After 5 wrong PINs a computer is locked for a minute (even for the right
  PIN), and “Wrong PIN from … too often” appears below address and PIN. If
  a stranger shows up in the table, select them and click **Remove**: the
  connection is dropped, and this computer cannot get back in until the
  session is closed. Computers that flood the trainer with connections or
  messages are disconnected automatically.
- The trainer does not pass on updates: it only tells its version number,
  the download always comes from GitHub.

## 8. Accessibility

### Announcements (F9)

The program uses its built-in voice to say what is otherwise only on
screen, without a screen reader. F9 switches announcements on and off
(also under “Settings …” → “Announce feedback”); the voice confirms it.
Announcements use the language of the interface: German with the Thorsten
voice, English with the LJ Speech voice. If the voice is missing, F9 and
F11 play an error tone and the reason appears in the status line. In the
settings you set the **Speaking rate** (70–200 %) and the **Announcement
volume** (25–100 %).

On the very first start the program says once that F9 switches
announcements on, F11 tells you where you are and F12 starts daily
practice (Mac: Cmd+Shift+T). If a screen reader is running (NVDA, JAWS,
Windows Narrator, VoiceOver or Orca), announcements are switched on right
away. So that the two voices do not talk over each other, mute your screen
reader or put it to sleep while practising:

- **NVDA:** NVDA+S until speech mode is “off”, or NVDA+Shift+S (sleep mode
  for this program; laptop layout NVDA+Shift+Z).
- **JAWS:** Insert+Space, then S (speech off and on again).
- **Orca:** Orca+S.
- **VoiceOver:** Ctrl silences it only briefly; to mute it for good use
  VoiceOver Utility, Speech section.

**Where am I? (F11)** reads out the tab, status, last feedback and
remaining time, even with announcements switched off. In Contest it gives
QSOs and rate; with the focus in the call or exchange field it also spells
what is in it. In daily practice it gives the current card or the running
block, the practice time and the stars, in the Statistics tab an overview
(overall result, most errors, confusions, review box, insights, seals,
practice today, comparison and week). F9 and F11 work in every window; in
Settings, Band conditions, Help and the network windows F11 says the name
of the window and the control you are on.

### What is announced

- **One by one:** in Groups, Words and Callsigns the result of each answer
  (“Right”, “Wrong. Listen again”, after the last attempt “Sent: kay, em,
  you. Typed: kay, em, em”), in head copy the solution. In Characters only
  errors (“Wrong. kay, not em”); correct answers get the feedback beep.
  The program waits until the announcement has finished.
- **Everywhere:** the result at the end of each run, the tab name when
  switching, the cards of daily practice and messages why a run does not
  start or stops.
- **QSO:** at the end, what to do next (“enter your log … F8 checks”) or,
  when typing along, the result in percent; in the quiz the name of the
  field when you enter it and, after “Check”, the result with the correct
  values.
- **Contest:** logging errors right after your TU (“Busted. Correct: Delta,
  Lima, One …”, “Wrong exchange”, “Not in log”); correctly logged QSOs stay
  silent so the rate does not suffer. Callsigns are spelled in the phonetic
  alphabet.
- **Speak:** the tab speaks by itself while practising; announced are only
  why it does not start, the end and the MP3 export.
- **Network as a participant:** connecting, disconnecting and being
  rejected; after each answer “Right” or “Wrong. It should be: kay, em,
  you” (not with fixed pace); the result at the end. New sequences from the
  trainer take priority and interrupt an announcement. **As trainer**,
  address and PIN are announced when the session opens; F11 repeats them.
- **Daily practice:** the card before a block names the stars already
  earned; the evening summary is read out in full, then “Enter: Done” and,
  if offered, “With Tab: 5 more min …”. F11 in the window repeats it.
- **Award window:** new seals with condition and date.
- **Windows:** when a window opens, it says its name. When you close one,
  you hear where you are (“Back in the main window. Tab One by one,
  Groups.”).

### Using the keyboard

- **Controls:** when you Tab into a field, button or check box, the
  announcement says what it is and how it is set (“High contrast, check
  box, off”, “Speed, number field, 20 WPM”). Changes with the space bar,
  arrow keys or in a list are announced too. When the program sets the
  focus itself (e.g. into the answer field), it stays silent. A row of
  option buttons (such as “Content”) is a single Tab stop; within it the
  arrow keys choose.
- **Typing:** in the settings fields and in all number fields each typed
  character is spelled out, deleted ones with “deleted”. Not in the answer
  fields of the exercises: there the announcement would cut off the Morse
  tone.
- **Tables** (statistics, awards, contest log): when you Tab into one, the
  announcement gives name, role and number of rows and the first row right
  away; with the arrow keys each row is read out with the column names. If
  columns are hidden, the left and right arrow keys show more.
- **File paths:** messages such as “Saved: …” read out only the file name,
  error messages the whole path.
- All keyboard shortcuts are in section 9.

### Seeing

- **Font size:** Ctrl+Plus, Ctrl+Minus, Ctrl+0 (section 2); the new size
  is announced unless a long Morse tone is playing. With a large font the
  tab scrolls to the feedback after each answer. At 150 to 200 % tables
  show fewer rows (at least 4) so that they do not grow taller than the
  screen; below them a line reads “Rows 1 to 4 of 15, more with arrow
  down”.
- **High contrast:** “Settings …” → “High contrast (black, white, yellow)”,
  takes effect after a restart (**Restart now** button). Black background,
  white text, yellow main buttons and highlights, strong borders; all text
  stands out from its background by at least 7:1.
- Right and wrong are always shown as text too, not only as colour.

## 9. Keyboard shortcuts

On the Mac, Alt+digit and the shortcuts with letters use Cmd instead of
Alt or Ctrl (Cmd+1, Cmd+B, Cmd+Comma).

**Everywhere:**

- Alt+1 to Alt+7: the tabs One by one, Non-stop, Speak, QSO, Contest,
  Network, Statistics. Alt+0: Statistics. Ctrl+Tab: cycle through the tabs.
- F1: help at the section of the current tab (not in Contest). Ctrl+F1:
  help, also in Contest.
- F9: announcements on/off. F11: read out where you are. F12: start daily
  practice.
- Ctrl+Plus, Ctrl+Minus, Ctrl+0: font larger, smaller, normal.
- Ctrl+B: open band conditions (inside: Ctrl+P listens).
- Ctrl+Comma: settings.
- Ctrl+Q: quit the program (Mac: Cmd+Q; twice during daily practice).
- Tab, Shift+Tab: through fields, buttons and check boxes. Space, Enter:
  press a button; space toggles check boxes.
- Arrow keys: choose in lists, sliders, tabs, tables and the “Content” row
  (One by one, Non-stop, Speak).
- Esc: close secondary windows; in a practice tab stop the run.

**In single tabs:**

- **Daily practice:** Enter skips the card between blocks; Esc or F5,
  twice, ends daily practice.
- **One by one, Non-stop:** F5 starts and stops, Esc stops.
- **One by one:** Alt+1 (again) switches the content: Characters → Groups →
  Words → Callsigns. Space repeats. In head copy: Enter reveals, J = knew
  it, N = didn't. After a RufZ run: F6 replays the missed ones or the
  current one again, F7 starts from the beginning, Esc stops.
- **Speak:** F5 starts and stops, space repeats the current item, Esc
  stops.
- **QSO:** F5 new QSO or stop, F6 listen again, F7 show text, F8 check, Esc
  stops.
- **Contest:** F10 starts and ends (F5 before the start reminds you). F1
  CQ, F2 exchange, F3 TU/log, F4 my call, F5 their call, F7 “?”, F8 “AGN”.
  Enter sends the appropriate next message (ESM, “Enter Sends Message”),
  Esc aborts sending.
- **Network (trainer):** F5 start/stop, F6 repeat for everyone, F7 next.
- **Help:** Ctrl+F searches (Enter: next match, Shift+Enter: previous); the
  down and up arrows read the next or previous paragraph.

**On the Mac** F9, F11 and F12 are media keys or taken by the system
(Fn+F11 shows the desktop). Use Cmd+Shift+A (announcements on/off),
Cmd+Shift+W (where am I), Cmd+Shift+T (daily practice) and Cmd+Shift+H
(help) instead. Cmd+0 stays with the font (normal size) there.

**Searching the help** also finds what is written differently: umlaut
spelling and hyphens do not matter, other words for the same thing are
searched too (“hotkey” finds this section), otherwise parts of compound
words. If the term is only in the other tab (manual or changes), the search
says how often.

## 10. Installing and updating

### Linux and Windows

Ready-made programs are on the
[Releases](https://github.com/tilde1970/Morsetrainer/releases) page; you
do not need Python for them.

- **Linux:** download `Morsetrainer-x86_64.AppImage`, make it executable
  (`chmod +x Morsetrainer-x86_64.AppImage`) and start it. If it reports
  “No suitable fusermount binary found” or another FUSE error, the
  `fusermount` program is missing: install the `fuse3` package (Debian,
  Ubuntu, Mint: `sudo apt install fuse3`) or start the AppImage without
  FUSE: `./Morsetrainer-x86_64.AppImage --appimage-extract-and-run`. The
  AppImage exists only for 64-bit PCs (x86_64); on ARM devices such as the
  Raspberry Pi, run the Morsetrainer from source (see
  `docs/Entwicklung.en.md`).
- **Windows:** download `Morsetrainer.exe` and start it. Because the file
  is not signed, Windows SmartScreen warns you on the first start (“More
  info” → “Run anyway”). A virus scanner may also wrongly flag an unsigned
  file; the checksum shows that it is unchanged.

Next to the programs there is `SHA256SUMS.txt` with their checksums. To
check on Linux, run `sha256sum -c --ignore-missing SHA256SUMS.txt` in the
download folder; on Windows run `Get-FileHash Morsetrainer.exe` in
PowerShell and compare the value with the line in `SHA256SUMS.txt`.

### macOS

For Macs with an Apple processor (M1 and newer) from macOS 14 (Sonoma)
there is `Morsetrainer-macOS.zip`. Download it, unzip it (double-click, if
the browser has not already done so) and drag `Morsetrainer.app` into the
“Applications” folder. The app has been tested on a Mac with an Apple
processor; feedback on other Macs is welcome.

Because the app is not signed by Apple, macOS blocks the first start:

- **macOS 15 (Sequoia) and newer:** start the app once by double-click and
  close the message with “Done”. Then open “System Settings” → “Privacy &
  Security”, click “Open Anyway” at the bottom next to “Morsetrainer was
  blocked” and confirm with your password.
- **macOS 14 (Sonoma):** in the Finder right-click (or Ctrl-click)
  `Morsetrainer.app` → “Open”, then “Open” again in the message.

After that the app starts normally. If macOS says the app is “damaged”,
run this in the Terminal:
`xattr -dr com.apple.quarantine /Applications/Morsetrainer.app`.

There is no automatic update on the Mac, only a notice about a new
version: download the new ZIP file and replace the app in the
“Applications” folder. Your data stays. After every replacement macOS asks
for approval again.

### Older Macs with an Intel processor

They run the Morsetrainer from source:

1. Install Python 3.10 to 3.13 from
   [python.org](https://www.python.org/downloads/macos/), on macOS 13 or
   newer. This Python includes a working Tk; with the Python from Homebrew
   the window often stays empty or `tkinter` is missing. With Python 3.14
   the trainer runs on Intel Macs without speech (announcements, Speak
   tab). On macOS 12 and older the setup fails on the speech engine; use
   `pip install numpy sounddevice lameenc` instead of the line with
   `requirements.txt` (again without speech).
2. On the [Releases](https://github.com/tilde1970/Morsetrainer/releases)
   page, download “Source code (zip)” of the newest release and unzip it.
3. In the Terminal, change into the unzipped folder and set up once:

   ```
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   bash packaging/get_voice.sh
   ```

   The last command downloads the voices for announcements and the Speak
   tab (a good 120 MB); without it everything else works, just without
   speech.

4. Start with `python main.py`. Later, `source .venv/bin/activate` and
   `python main.py` in the same folder are enough.

Started this way, the data lives in the unzipped folder. To update, unzip
the new source, copy `stats/`, `window_state.json` and, if present,
`callsigns.scp` and `woerter.txt` from the old folder into it and repeat
step 3.

### Updates

At start the Morsetrainer checks in the background whether there is a newer
release. The “Update available” window shows what is new. With “Update
now” (Enter) it downloads the exe or AppImage from GitHub, replaces its own
file and restarts. With “Later” (Esc) the footer shows “Version …
available” with an “Update …” button that opens the window again; on its
own it asks again only after seven days. Without internet the program
simply runs as usual. Started from source and on the Mac there is only the
notice. If the file is in a folder without write permission, download it by
hand.

Downloads come only from this repository over HTTPS, and only a newer
version. The file must match the checksum in `SHA256SUMS.txt` of the same
release, otherwise it is discarded. This catches interrupted and damaged
downloads. It does not protect against a hijacked GitHub account, and
there is no signature.

### No sound?

The Morsetrainer always plays on the system's default output device; you
cannot choose another device in the program. If there is no sound or
“Keine Tonausgabe möglich” (no sound output possible) appears, check in
this order:

1. **Volume and mute** on the system and on the speaker or headphones. To
   hear something without practising, “▶ listen” in the lesson row of the
   One by one tab plays the new character.
2. **Wrong device?** If a monitor with speakers (HDMI) or a Bluetooth
   speaker is connected, it may be the default device. In the system's
   sound settings choose the device you want as default output.
3. **No device, or connected after the start?** If the Morsetrainer reports
   “Kein Audiogerät gefunden” (no audio device found) or “Das Audiogerät
   ist nicht mehr verfügbar” (the audio device is no longer available), or
   you connected a device after the start: the Morsetrainer only knows the
   devices from program start. Connect the device, choose it as default
   output in the system and restart the program.
4. **Message “Das Audiogerät ist belegt” (the audio device is in use):**
   another program has the device to itself (exclusive mode), such as SDR,
   logging or audio software. Release the device there or close that
   program.
5. **Message about the sample rate:** the device cannot do 48 kHz. Choose
   another device as default output in the system.
6. **Started from source:** `python main.py --selftest probe.mp3` checks,
   without a window and without sound, whether PortAudio, Tk and the
   voices are present, and says what is missing. On Linux `libportaudio2`
   and `python3-tk` belong here (see `docs/Entwicklung.en.md`).

If none of this helps, please report the message including the text in
brackets in the
[Issues](https://github.com/tilde1970/Morsetrainer/issues).

## 11. Data

### Where the data lives

Started from source, the data lives in the program folder; with the
AppImage in `~/.local/share/morsetrainer/`, with the exe in
`%APPDATA%\Morsetrainer\`, with the Mac app in
`~/Library/Application Support/Morsetrainer/`. “Settings … → Data → **Open
data folder**” shows it in the file manager.

- `stats/morsetrainer.db`: all practice data in one SQLite database (runs,
  overall statistics, review box, daily practice with stars, lesson and
  speed, practice time, awards). Every row is saved at once. After a crash
  the Morsetrainer adds the interrupted run to the statistics at the next
  start; only that run's practice time is missing.
- Copies next to the database: `morsetrainer.db.defekt-<time>` is a damaged
  file that the Morsetrainer set aside; it then starts a new one.
  `morsetrainer.db.vor-v<number>` is the copy from before a format
  change, `vor-import-<time>.zip` the state from before restoring a
  backup. All three may be deleted once everything works. When you restore
  a backup, existing `.defekt-…` and `.vor-v…` files go to `stats-gerettet/`.
- `auto-sicherung/`: the automatic weekly backups and, if one failed,
  `auto-sicherung-fehler.txt`.
- Also in `stats/`: the award last opened (`diplom.html`) and the CSV
  tables from the Network tab (`…-netzwerk.csv`). Practice data from
  version 2.27 and older is taken into the database by the first start of a
  newer version and moved to `stats/alt-json/`.
- `window_state.json`: window size and all settings, including the
  language.
- `callsigns.scp`: callsign list (Super Check Partial), **not included in
  the repository**. The “Load callsign list” button in the One by one tab
  saves it here (see the One by one tab). Without the file the trainer
  makes up callsigns from country patterns.
- `woerter.txt`: your own words for “Abbreviations” in One by one (Words)
  and Non-stop, one per line, optionally with a meaning:
  `DOK = Distrikts-Ortsverbandskenner`. The “Edit own words” button creates
  the file with instructions and opens it. The words are added to the
  built-in ones.
- `fehler.log`: log of unexpected program errors. When one happens, a
  window names the path of the file once; please attach it when you report
  the error (Issues on GitHub). Above 1 MB it starts over.

### Notices at start

If the database cannot be opened as usual, a notice window appears at
start. Its title says what it is about:

- **Daten von neuerer Version** (data from a newer version) and **Daten
  nicht aktualisiert** (data not updated): the data comes from a newer
  version or could not be converted. It stays unchanged, statistics, awards
  and daily practice are empty, and new results are not saved. Remedy:
  update the Morsetrainer (section 10, “Updates”).
- **Daten beiseitegelegt** (data set aside): the file was damaged. The
  Morsetrainer set it aside as `morsetrainer.db.defekt-<time>` and starts
  anew; statistics, awards and daily practice are empty at first. Bring
  the data back as described under “Restoring a backup” and “Bringing data
  back by hand”.
- **Automatische Sicherung gescheitert** (automatic backup failed): the
  backup at the last exit did not work, the window gives the reason. Check
  the free space on the disk or back up by hand.

### Backing up and moving to a new computer

Under “Settings … → Data”, **Back up …** saves all settings and data
(`stats/`, `window_state.json`, `woerter.txt`, `callsigns.scp`) into a ZIP
file in a place of your choice, such as a USB stick. The database goes in
as a consistent state, even while you are practising. The voices
(`voices/`) are not included; they are inside the AppImage or exe.

### Restoring a backup

This is how to bring a backup back on the same or a new computer:

1. Close all other Morsetrainer windows. Open “Settings … → Data” and
   choose **Restore …**.
2. Choose the ZIP file. The database is checked first.
3. Confirm the question. The current state is saved first as
   `vor-import-<time>.zip` in the data folder; the three newest such files
   are kept.
4. The program quits. Start it again; now the restored settings apply.

`stats/` is replaced completely, the other files as far as they are in the
backup. Backups from version 2.27 and older can still be restored.

### Automatic backup

The Morsetrainer backs up by itself: on exit it creates a backup
`auto-<date>.zip` in the `auto-sicherung/` folder of the data folder, at
most every 7 days. The last 4 are kept, older ones are deleted; if the
Morsetrainer has set a damaged file aside, the older backups before that
are kept. You can switch this off under “Settings … → Data” with the
**Back up automatically (weekly, on exit)** switch.

- The automatic backup is in the data folder. It protects against a
  damaged database, not against a disk failure; for that, also back up by
  hand to a USB stick.
- To restore: as above with **Restore …**; the files are in
  `auto-sicherung/` (**Open data folder** button).
- If the backup fails, for example because the disk is full, the
  Morsetrainer reports it at the next start in the window “Automatische
  Sicherung gescheitert”.

### Bringing data back by hand

You need this only if a damaged database was set aside and you hope to
rescue something from it. Usually **Restore …** from a backup is easier.
The files are in the `stats/` folder of the data folder.

1. Quit the Morsetrainer.
2. Delete the existing files `morsetrainer.db-wal` and
   `morsetrainer.db-shm`, if they exist. Otherwise a foreign journal acts
   on the restored file without any message.
3. Move the new `morsetrainer.db` somewhere else (or delete it if the new
   data is worthless). Then rename `morsetrainer.db.defekt-<time>` to
   `morsetrainer.db`. If `morsetrainer.db.defekt-<time>-wal` is next to it,
   it belongs with it: rename it to `morsetrainer.db-wal`.
4. Start the Morsetrainer.

### Deleting all data

Anyone who wants to delete all their data deletes not only `stats/` but
also the `auto-sicherung/` folder, the `stats-gerettet/` folder, the
`vor-import-<time>.zip` files and the `.defekt-*` files in the data
folder: they contain copies of the practice data. Add `window_state.json`
(callsign, name, locator, network name) and `fehler.log` (paths with your
user name).
