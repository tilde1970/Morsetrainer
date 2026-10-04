# Morsetrainer – Manual

A CW trainer for everyone from beginners to contesters, developed by
**DL4YM**. This manual is also available in the program under **Help**. A
short overview with pictures is in the [README](../README.en.md).

**Language:** the program starts in German. Switch to English under
„▸ Weitere Optionen“ → „Sprache / Language“; it takes effect after a
restart.

## Training modes

| Tab | What you practise |
|---|---|
| **Characters** | Recognise single characters; after each answer you see your time and the current limit, e.g. “0.38 s, limit 1.20 s”. With time limit (Instant Character Recognition): the limit gets shorter while you answer reliably and longer when you miss characters; a confusion leaves it unchanged. After a confusion you hear the correct character and the one you typed back to back. |
| **Groups** | Copy groups of characters. The group length can grow: start short, one longer after 5 correct groups, one shorter after 2 wrong groups (each on the first attempt). |
| **Words** | CW abbreviations, Q codes and QSO words, only from characters you already know. The default is “Listen first”: hear the whole word, then type; a slow answer is noted. R, K and the prosigns KN and SK also appear (but do not count as words for the minimum). A weak character comes up more often, but in changing words. The meaning is shown after the answer. You can add your own words (see Data). |
| **Callsigns** | Real callsigns from the Super Check Partial list, by default only from characters you have already learned (from Koch lesson 23 with the first digit). Occasionally with /P, /M, OE/… as in contests. Optionally as a **RufZ run** (modelled on RufzXP): 50 callsigns, one attempt each, the speed grows, score = length × effective speed, best score (with starting speed) and history; afterwards you can replay the missed and slowly recognised callsigns (F6): first just listen, then again with the solution, at the original speed. |
| **Continuous** | The audio keeps running without waiting, you type along (as when listening on the air); characters come in groups (default 5) with a word gap in between. Instead of random characters also as **plain text**: words, typical QSO phrases (“TNX FER CALL”, “UR RST 599”), callsigns or complete QSOs in one go (plain text does not count for the lesson). Optionally with **band conditions** (light, medium, heavy) running under the whole session. After stopping (F5 or Esc) a comparison shows the last characters; **Everything in a separate window** shows the whole session, split into the groups as sent (without groups in blocks of 5), errors in red, larger/smaller font, copyable – or only the sent text, to check against your paper. A key only counts if it fits the character: not guessed in advance and at most 5 s after it; typing too much counts as an error. |
| **Speak** | Listen & say without a keyboard (like Morse Code Ninja): Morse code, a thinking pause in which you say out loud what you heard, then a voice announces the solution – characters, groups and callsigns spelled (German letter names or phonetic alphabet), words and phrases as a whole or with their meaning – and the code comes once more. The thinking pause is deliberately short (default 1 s plus 0.3 s per character). Content: characters, groups, words, phrases, callsigns. **Save as MP3** for on the go (phone, car). Counts only for practice time. *The voice is German.* |
| **QSO** | Listen to complete QSOs: normal QSO or contest runs (CQ WW, CQ WPX, WAG, ARRL DX, IARU HF) with adjustable pile-ups (default off). Evaluation via log check, by typing along, as **head copy + questions** (no notes, afterwards content questions about name, QTH, rig, weather … or exchange) or listen only. Next to the length the estimated duration is shown; how often you used “Again” before checking is noted. |
| **Contest** | You are the running station (similar to Morse Runner): call CQ, pick up callers, send the exchange, log. As in a real contest, callers sometimes answer to an almost correct call – if you notice the mistake, correct the call and confirm with Enter (“Call TU”), otherwise “Busted” appears in the log. “?” in the call field asks back (DL1?, DL?ABC). Speed and pitch spread of the callers are adjustable, at the end there is a summary by type of error; F10 starts and ends. |
| **Network** | Practise as a group on the local network (class, club evening): a trainer sets the pace, everyone hears the same sequence on their own headphones and copies it; the trainer sees live who typed what. See below. |
| **Statistics** | Overall statistics per character (only from random characters and callsigns; in words, phrases and QSOs the context gives away too many characters), **spaced repetition** (review over days: characters recognised reliably and quickly come back after 1, 2, 4 … 32 days, uncertain ones the next day; decided once a day from 5 attempts, promoted only from random characters; due ones come up more often with “weak favoured” and can be practised specifically), most frequent confusions (with a button to practise them), daily goal, **awards** and **lifeline** (see below) and progress history per mode. |

In **Groups, Words and Callsigns** you can choose:

- **Input:** *Copy while listening* (type while the audio plays), *Listen
  first* (type after the audio) or *Head copy* (type nothing; Enter reveals,
  then J = knew it, N = didn't). Head copy relies on your own assessment and
  therefore does not count for the overall statistics and the lesson.
- **Speed adapts** (as in RufzXP): correct on the first attempt +1 WPM,
  wrong on the first attempt −1 WPM – meaning the effective speed. With
  Farnsworth the gaps get shorter first; once they are gone, the character
  speed increases. The characters get slower only down to 18 WPM, below that
  the gaps get longer, so you cannot count dits and dahs. The same rule
  applies to “Adjust speed automatically” in the QSO tab. The progress
  history shows the effective speed (e.g. 10 at 20/10 WPM).
- **Band conditions** in three levels: light, medium, heavy. They also run
  under the start sign (VVV =) and the end sign (+).

## Daily practice

Can't be bothered to decide what to practise today? **▶ Daily practice
(10 min)** at the top (or F12) puts together ten minutes from whatever is
due and switches the tabs by itself:

| Level | Warm-up | Main part | Wind-down |
|---|---|---|---|
| Lesson 1–9 | Characters with time limit, 3–4 min | Groups, fixed speed | Continuous, groups of 3, 2 min |
| Lesson 10–29 | as above | as above | Words, 2 min |
| Lesson 30–41 | as above | as above | Words or callsigns on alternate days, 2 min |
| after Koch (lesson 41 passed) | Characters, 2 min | Continuous, groups of 5, 4 min | Callsigns, 4 min |

- **Warm-up** with all characters of the lesson; those due today in the
  review box come more often, or, if nothing is due, your most frequent
  confusions. With many due characters it gets a little longer and the
  main part correspondingly shorter. The time limit continues where it
  ended last time and is never longer than 1.5 s here.
- **Speed:** the main part keeps a fixed speed (characters at least
  18 WPM). It changes once a day, effective from the next: below 75 % on
  the first try (at least 100 characters) 1 WPM slower. After Koch, 90 % or
  more also makes it 1 WPM faster; not before, because a good day then
  already brings the next character.
- **Lesson:** if the main part meets the Koch criterion (50 characters,
  90 % on the first try), the next lesson applies from the next day – no
  question asked. The daily practice keeps its own lesson for this (the
  first time the one from the header); lesson and character set at the
  top stay as you set them for free practice.
- **Three stars a day:** ★ *Showed up* for the full 10 minutes, ★ *Clean*
  for 90 % on the first try in the main part (80 % in the first three days
  of a new lesson), ★ *Ahead* for real progress: next lesson earned, a
  character reaching box 3 of the review box for the first time, or a
  daily speed you never had before. A second daily practice on the same day can add
  missing stars; earned stars are never lost, not even when you stop early.
- **Between the blocks** a short card shows the result, new stars and
  what comes next. It stays until you continue with Enter or “Continue”;
  Esc ends the daily practice.
  Afterwards the tab settings are back as they were.
- **Evening summary:** stars, what improved compared with the week before
  (reaction time per character in Characters, group score; only with
  enough data and at the same speed, never “worse”), how much is missing
  for the next lesson, where you stand on the weekly goal and, if the main
  part went well, once a day **5 more min** with something different:
  your confusions within the lesson, a RufZ run or words.
- **Week:** next to the button is the week strip from Monday, e.g.
  “Mon ★★★  Tue ★★  Wed ✓  Thu –  Fri ·” (✓ = practised freely without the
  daily practice, daily goal reached; – = no practice), and next to it
  where you stand on the **weekly goal of 12 stars**. Four to five days of
  practice get you there; a missed day doesn't cost you the week. Until
  the first daily practice of a new week it shows a look back, e.g.
  “Last week: 4 days, 11 ★, lesson 12 → 13”.

## Awards

Like DXCC or WAC on the air: awards for what you can do for good, in the
levels **Bronze, Silver, Gold** and some in **Platinum**. They are checked
after every exercise; a new seal shows a window with the date and a
**Print** button – the award opens as a certificate in the browser (A4
landscape) with your callsign and name from “▸ More options” (which you
can also change in the window). During the
daily practice the window comes only after the evening summary, which
also mentions the new seals from the daily practice.

The overview is in the **Statistics** tab under “Awards”: all awards with
the seals achieved, the next goal (e.g. “Silver: 18 / 25 lessons”) and
from which lesson it can be reached; open ones are grey. Club night only
works together in the network and is listed last while it has no seal. A selected row
shows the condition and the days of the seals, for QRN-proof, Contest and
Confusion also how close you are to the next level (best run or the next
pair with the days left); “View and print award” shows the award of the
highest level.

| Award | Levels | From lesson | Condition |
|---|---|---|---|
| Koch | Lesson 10 / 25 / 41 | 1 | Passed lesson run: ≥ 50 characters, ≥ 90 % at the first attempt, characters ≥ 18 WPM (groups or continuous) |
| Worked All Letters | 10 / all 26 letters in box 3; Gold: all in box 6 and all digits in box 4 | 1 | Spaced repetition; the highest box ever reached counts, reached with characters ≥ 18 WPM |
| Copying in flow | 10 / 15 / 22 WPM effective | 15 | Continuous with plain text (words, phrases, QSO; Gold only phrases or QSO), character set at least lesson 15, full 3-min run, ≥ 90 % minus extra keys, characters ≥ 18 WPM. With your own words from `woerter.txt`, “words” does not count |
| QRQ | 20 / 25 / 30 / 35 WPM | 40 | Continuous with random groups (≥ 5 characters) from the full character set, no Farnsworth, full 3-min run, ≥ 90 % minus extra keys |
| QRN-proof | band light 90 % / medium 90 % / heavy 85 % | 25 | Groups or continuous, ≥ 200 characters, noise volume ≥ 100 % for the whole run, characters ≥ 20 WPM, effective ≥ 12 WPM; in groups the first attempt in time counts |
| Rufz | 2,000 / 3,500 / 5,500 / 7,500 points | 27 | Full run with 50 calls, no prefix filter, starting speed ≥ 20 WPM |
| Contest | see right | 41 | Run ≥ 10 min; Bronze: ≥ 20 WPM, 10 QSOs in 10 min, ≤ 10 % errors; Silver: ≥ 25 WPM, activity ≥ 2, 20 QSOs, ≤ 5 %; Gold: ≥ 30 WPM, activity ≥ 3, 25 QSOs, at most 1 error |
| WPX | 100 / 400 / 1,200 / 2,000 prefixes | 25 | Different WPX prefixes, right at the first attempt (callsigns and contest, there without asking for the call again), characters ≥ 18 WPM |
| Headphones | 15 / 20 / 25 WPM effective | 41 | 3 normal QSOs in a row with “Head copy + questions”, all questions right, without “Again”, characters ≥ 18 WPM; Silver and Gold with the length Normal or Long. Skipping a QSO without “Check” breaks the run |
| Confusion overcome | 1 / 3 / 6 pairs | 5 | A pair that was among your most frequent confusions, confused at most once in 28 days with ≥ 40 attempts each |
| Endurance | 10 / 50 / 150 / 365 days | – | Days with ≥ 10 min practice, not in a row |
| Characters heard | 5,000 / 25,000 / 100,000 / 250,000 | – | Correctly recognised random characters, characters ≥ 18 WPM |
| Club night | 1 / 5 / 15 / 40 evenings | – | Days with ≥ 10 min of network sessions in total, taken part in or led as trainer (only runs with participants) |
| First QSO understood | – | 40 | Normal QSO with questions, all right, without “Again”, ≥ 15 WPM effective, characters ≥ 18 WPM |
| Worked All Contests | – | 41 | All 5 contest types with ≥ 30 QSOs each and ≤ 10 % errors |
| Q-code expert | – | 40 | Each of the 20 Q codes right 3× at the first hearing, on at least 2 days, characters ≥ 18 WPM |
| All digits | – | 39 | All 10 digits at least in box 3, reached with characters ≥ 18 WPM |

- For Koch, flow, QRQ, QRN-proof, Rufz and contest, **Silver and above need
  two different days** – one lucky run is not enough. Starting straight at
  lesson 41 gives Bronze on the first day and Silver and Gold with another
  passed run on a different day.
- Only runs without self-assessment count.
- Seals achieved are kept with their date in the database and are
  never lost, not even with “Reset overall statistics”.
- On the first start with awards, whatever follows from your practice so
  far is filled in quietly (with the day it was reached); one note says
  how many awards that is.

## Lifeline

Below the awards on the **Statistics** tab, the **lifeline** shows the long
road from your first practice until today: daily-practice stars added up,
the highest Koch lesson practised (up to the final lesson 41) and the
daily speed of the daily practice, with the award seals underneath as
diamonds in their colour. All three lines only rise or stay level; hover
with the mouse to see the values and seals of each day. The lifeline stays
complete after “Reset overall statistics”.

## Learning path for beginners

1. Set **Koch lesson** at the top to 1 (K and M). The default is **Koch
   speed 20/10** (can be restored at any time under “▸ More options”): the
   characters come fast enough that you hear them as a sound pattern
   instead of counting dits and dahs, with longer gaps in between.
   “▶ listen” plays the new character.
2. Get to know the characters in the **Characters** tab. The **time limit**
   is on from the start: there is no time to count dits and dahs, the
   character has to come as a sound pattern. A wrongly recognised character
   is played again right away while the solution is shown; it is asked
   again only after a few other characters. The space bar repeats a
   character but does not extend the deadline; recognised only after the
   repeat counts as not recognised. After a session with at least 50
   characters and 90 % correct – with time limit from start to finish, at
   most 1.5 s at the end – the app suggests continuing with groups.
3. Practise in the **Groups** tab. Copy while the audio plays, as with
   single characters. After an error you see and hear the solution, then
   it goes on as on the air; weak characters come back later through the
   weighting. Under “Show solution after” you can allow up to 3 failed
   attempts: then only the wrong positions are marked at first and the
   group comes again.
4. If you get 90 % on the first attempt in a session of at least 50
   characters in groups (or in Continuous mode), the next lesson is
   offered. A first attempt only counts for the lesson if you did not repeat
   the group with the space bar and answered quickly (1.5 s plus 0.6 s per
   character after the end of the tone); typing too much counts as an
   error. Weak and new characters automatically come up more often. After
   the 40 lessons of lcwo.net, lesson 41 completes the course: all
   characters, none favoured as new any more (weak ones still come more
   often). If you like, lessons 42–45 then add the prosigns from QSOs:
   AR (key `+`), KN (`(`), SK (`*`) and BK (`#`). The trainer does not
   move there by itself; set the lesson at the top. After that, the next
   prosign is offered again. The daily practice also repeats prosigns you
   have learned.
5. From lesson 6 there are enough words for the **Words** tab (words with
   the newest character are favoured), then **Continuous** and **QSO**.
6. In the **Statistics** tab (confusions of the last 30 days), “Practise the
   4 most frequent” shows which characters you confuse and practises exactly
   those against each other. “↩ Lesson” at the top takes you back to your
   lesson.

Also helpful:

- **Short and daily** beats long and rare: the footer shows today's
  practice time and the daily goal (adjustable in the Statistics tab), the
  week strip at the top the days you practised.
- **Vary pitch and speed slightly** (shared setting): if you only ever hear
  exactly one sound, you will find it harder on the band.
- **Callsign and name:** enter them once under “▸ More options”. They
  appear on the awards and are the default for “My callsign” in Contest and
  “Name/callsign” in Network (there the callsign if there is no name).
  Both fields follow along until you enter something else there, such as
  a contest callsign. Without a callsign of your own the name is enough: it
  then appears alone on the award; for the contest you enter a made-up
  callsign there.

## Band conditions (QSO and Contest)

Each can be switched on and adjusted: noise, static crashes (QRN), QSB,
chirp, SSB babble and CW QRM on the adjacent frequency.

## Network: practising as a group

For classes and club evenings: all computers are on the same network
(Wi-Fi or LAN), one is the trainer, the others join as participants. Only
text is sent; each computer generates the sound itself – no dropouts,
with its own headphones and its own pitch.

**Trainer:** in the *Network* tab choose “Trainer”, **Open session**. The
address and a four-digit PIN for the participants are shown. Then choose
content (characters, groups, words, callsigns, phrases, QSO plain text
or **own text**, one line per sequence; prosigns as + for AR, ( for KN,
* for SK, # for BK), number of sequences (for QSO plain text whole QSOs,
sent in sections up to the next =, K or closing sign such as
“UR RST 599 599 =”), answer time and band conditions; character
set, speed and Farnsworth come from the header. At a slow character speed
(below 18 WPM) the header points out in every tab that the characters
can be counted and offers Koch speed 20/10. After **Start** the start sign VVV = comes first
(can be switched off), and the end sign + after the last sequence. Then
everyone gets the same sequence at the same time. The next one comes once everyone has
answered or the answer time is up (or with **Next**); **Repeat for
everyone** plays the current one again. The table shows each
participant's current answer, share of correct characters, how many
sequences were **fluently** correct and typical time from the end of the
tone to Enter, and below it the group: accuracy, share of fluent
sequences, most common errors, weakest characters. Fluent means correct
on the first hearing and fast enough that nobody counted – within the
same window as in the Groups, Words and Callsigns tabs (1.5 s plus 0.6 s
per character after the tone). The answer time is only the hard limit.
Clicking a participant shows their errors and weakest characters. With
many participants the table can be moved **into a separate window** (for a
second screen or a projector); F5–F7 work there too, closing it brings the
table back into the tab. After
enough sequences at the same speed (50 characters across everyone) there
is a **speed recommendation**: faster from 90 % fluent, slower below 75 %,
applied with a button in steps of 1 WPM effective. **Save as CSV** stores
a table
in `stats/`: one row per participant with accuracy, fluent sequences, most
common errors and weakest characters, one column per sequence (with speed;
↻ = repeated for everyone) with what was typed and the time to answer.

**Fixed pace (copying on paper):** under *Flow* choose the fixed pace
instead of “Wait for answers” – for classes where not everyone has a
computer. The next sequence then comes after the tone plus a **writing
pause**, whoever has answered. The pause is the same for every sequence;
its default depends on the content (characters 2 s, words 3 s, groups,
callsigns and own text 4 s, phrases and QSO 5 s), because too much time
invites brooding. Until the end the trainer's screen shows no solution –
it may be on the projector: the status only says “No. 7 of 20”, the table
only whether an answer came in, results and own text are hidden. **Repeat
for everyone** (F6) stays for emergencies and extends the deadline;
**Next** (F7) moves on at once. Blocks of 20–25 sequences with solutions
in between work better than “until Stop”. Anyone taking part with just
pen and paper needs neither a computer nor a login but listens through the
trainer's speakers, so switching to the fixed pace turns on “Also play on
this computer”. They check their own copy against the solutions – or
hand in their sheet, and after the run the trainer types it in under
**Enter paper sheet** (name, then the line for each number, empty =
missed; the same name replaces the sheet). Anyone with a computer who
still wants to copy with a pen ticks “With fixed pace, copy on paper and
type it in at the end” when connecting: the input field stays closed
during the run, afterwards there is one field per number to type in the
copy, and **Evaluate** sends it to the trainer. Typed-in answers count for
right/wrong, errors and weak characters, but without timing: not as
fluent and not for the speed advice, and in one's own statistics not for
weighting and spaced repetition. The table shows “Paper” for them.

**Print answer sheet** (with the fixed-pace options) opens a sheet in the
browser for printing: name, date, numbered lines column by column as in
the solutions – with one box per character for groups and single
characters, otherwise a blank line; as many lines as set (25 for “until
Stop” and QSOs).

**Sound for everyone from the speakers:** with “Sound for everyone only
from this computer (speakers)” only the trainer's computer plays; the
participants' computers stay silent and are only used for typing. Nobody
needs headphones and everyone hears the same thing at the same time –
otherwise each computer plays slightly offset, depending on the network
and sound card. The participants' computers measure the time to answer
from when the sequence arrived. In this case the solution is played once
for everyone over the speakers as soon as someone did not have it
fluently correct. This works in both flows and suits the fixed pace when
paper and computers are mixed.

**Continuous:** under *Flow* choose “Continuous” and set the
**duration** in minutes. Groups (or words, callsigns …) then come without
pauses as in the *Continuous* tab until the time is up; everyone types
along continuously, without Enter. Scoring happens at the end as there: a
key only counts if it fits the character in time. Each participant
reports their result per group, so the table, solutions (numbered groups)
and CSV work as usual; during the run the trainer screen shows nothing
that gives away solutions, as with the fixed pace, only the remaining
time. Stopping early scores up to that point. Band conditions lie under
the whole run; own text is not available here.

**Solutions:** the button next to “Save as CSV” opens a separate window
for the projector, in both flows. During the run it shows the current
number in large type (“Missed one? Leave a gap and carry on with the next
number.”), afterwards all solutions numbered, column by column from top
to bottom as on paper, in a monospaced font; ↻ marks what was repeated
for everyone. A−/A+ (or +/−) change the font size, **Copy** puts the list
on the clipboard. Clicking a solution – or the arrow keys and space –
plays it again on the trainer's computer without interference, so
reading the answers becomes hearing them again.

**Participant:** choose “Participant”, enter name or callsign and the PIN,
**Search** (or enter the trainer's address) and **Connect**. You type
while the tone is still running; the answer is done with the last
character, Enter is only needed if you have fewer characters. There is
one attempt per sequence, then the solution is shown. If it was not fluently correct,
the sequence is played again with the solution (the trainer can switch
this off). If you are not finished in time, what you have typed so far is
scored. At a fixed pace it then only shows “No. 7 noted”; the solutions
come at the end as a list with sent, typed and ✓/✗, and each sequence can
be heard again with a double-click or space. The results count for your
own statistics like a normal run,
with the time per character as when copying along; after “Repeat for
everyone” or when too slow, a correct character counts as uncertain and
comes up more often with “weak favoured”. Practice time only counts while
a run is going, not while waiting for the trainer.

The trainer needs port 7373 (TCP) and 7374 (UDP) for the search. On
Windows the firewall asks the first time – allow it for private networks.
If the search finds nothing (some Wi-Fi networks block broadcasts), enter
the address shown by hand.

If the trainer has a newer program version, the participant is asked on
connecting whether to download it (see *Updates*); the Morsetrainer then
restarts and connects to the trainer again.

**Security:** the connection is not encrypted, and the four-digit PIN only
prevents mistakes, not attackers. Anyone reading along on the same network
sees names, practice text and answers and could log in with the PIN. Network
mode is meant for a club or home network; on unfamiliar or public Wi-Fi
(hotel, café, fair) better not open a session, and close the session after
the class. The trainer does not pass on updates: it only tells its version
number, the download always comes from GitHub (see *Updates*).

From version 2.31 on, the trainer slows down PIN guessing: after 5 wrong
PINs the computer is locked for a minute (even for the right PIN), and
“Wrong PIN from … too often” appears below address and PIN. If a stranger
shows up in the table, select them and click **Remove**: the connection is
dropped, and this computer cannot get back in until the session is closed.
The trainer also disconnects computers that flood it with connections or
messages.

## Help in the program

The **Help** button on the right of the footer shows the changes of the
versions (CHANGELOG) and this manual.

## Keyboard shortcuts

- **Daily practice:** F12 starts, Enter skips the card between blocks, Esc
  stops.
- **Characters, Groups, Words, Callsigns:** the space bar repeats.
  Head copy: Enter reveals, J = knew it, N = didn't.
- **RufZ (after the run):** F6 replay missed callsigns or the current one again, F7 from the start, Esc stop.
- **Speak:** F5 start/stop, the space bar plays the current item again, Esc stops.
- **QSO:** F5 new QSO/stop, F6 listen again, F7 show text, F8 check.
- **Network (trainer):** F5 start/stop, F6 repeat for everyone, F7 next.
- **Contest:** F1 CQ, F2 exchange, F3 TU/log, F4 my call, F5 their call,
  F7 “?”, F8 “AGN”. Enter sends the appropriate next message (ESM), Esc
  aborts sending.

## Download

Ready-to-run programs are on the
[Releases](https://github.com/tilde1970/Morsetrainer/releases) page:

- **Linux:** download `Morsetrainer-x86_64.AppImage`, make it executable
  (`chmod +x Morsetrainer-x86_64.AppImage`) and run it.
- **Windows:** download and run `Morsetrainer.exe`. The file is not signed,
  so Windows SmartScreen warns on first start (“More info” → “Run anyway”).

No Python installation is needed.

From version 2.30 on, `SHA256SUMS.txt` with the checksums sits next to the
programs. To verify, on Linux run `sha256sum -c --ignore-missing
SHA256SUMS.txt` in the download folder; on Windows run `Get-FileHash
Morsetrainer.exe` in PowerShell and compare the value with the line in
`SHA256SUMS.txt`.

### macOS

For Macs with Apple silicon (M1 and newer) there is
`Morsetrainer-macOS.zip`. Download it, unpack it (double-click, unless the
browser has already done so) and drag `Morsetrainer.app` into the
Applications folder. The app has not been tested on a Mac yet – feedback is
welcome.

As the app is not signed with Apple (that needs a paid Apple developer
account), macOS blocks the first start:

- **macOS 15 (Sequoia) and newer:** Double-click the app once and close
  the message with “Done”. Then go to “System Settings” → “Privacy &
  Security”, scroll down to “Morsetrainer was blocked”, click “Open
  Anyway” and confirm with your password.
- **macOS 14 and older:** In the Finder, right-click (or Ctrl-click)
  `Morsetrainer.app` → “Open”, then “Open” again in the message.

After that the app starts normally. If macOS says the app is “damaged”,
run `xattr -dr com.apple.quarantine /Applications/Morsetrainer.app` in the
Terminal.

The data lives in `~/Library/Application Support/Morsetrainer/`. There is no
automatic update on the Mac, only the hint about a new version; then
download the new ZIP file and replace the app in the Applications folder.
Your data stays where it is. After each replacement macOS asks for the
approval again.

**Older Macs with an Intel processor** run the Morsetrainer from source:

1. Install Python 3.10 or newer from [python.org](https://www.python.org/downloads/macos/).
   This Python comes with a working Tk; with Homebrew's Python the window
   often stays empty or `tkinter` is missing.
2. On the [Releases](https://github.com/tilde1970/Morsetrainer/releases)
   page, download “Source code (zip)” of the latest release and unpack it.
3. In the Terminal, change into the unpacked folder and set it up once:

   ```
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

4. Start with `python main.py`. Later, `source .venv/bin/activate` and
   `python main.py` in the same folder are enough.

Run this way, the data lives in the unpacked folder. To update, unpack the
new source and copy `stats/`, `window_state.json` and, if present,
`callsigns.scp` and `woerter.txt` from the old folder into it.

### Updates

On start the Morsetrainer checks in the background whether there is a newer
release and then asks whether to download it. With “Yes” it downloads the
exe or AppImage from GitHub, replaces its own file and restarts; with “No”
it does not ask again for this version, the footer just shows “Version …
available”. Without internet nothing happens, the program runs as usual.
Run from source or on the Mac, there is only the hint. If the file is in a
folder without write permission, please download it by hand.

Downloads come only from this repository over HTTPS and only for a newer
version. The file has to match the checksum in `SHA256SUMS.txt` of the same
release, otherwise it is discarded and the program stays as it is. This
catches interrupted and damaged downloads. It does not protect against a
compromised GitHub account – whoever can replace the release can replace
the checksum too; there is no signature.

## Data

When started from source, the data lives in the program directory; for the
AppImage in `~/.local/share/morsetrainer/`, for the exe in
`%APPDATA%\Morsetrainer\`, for the Mac app in
`~/Library/Application Support/Morsetrainer/`.

- `stats/morsetrainer.db`: all practice data in an SQLite database – every
  run with its characters, results of QSO checks and contests, overall
  statistics, review box, daily practice with stars, lesson and daily
  speed, practice time per day and the awards achieved. Every line is
  saved immediately; a crash costs at most the current one. If the file is
  damaged, it is set aside as `morsetrainer.db.defekt-<time>` and a new
  one is started.
- Also in `stats/`: the award opened last (`diplom.html`) and the CSV
  tables from the Network tab (`…-netzwerk.csv`).
- Up to version 2.27 the practice data lived as separate files in `stats/`
  (`*.jsonl`, `all_time.json`, `review.json`, `daily.json`, `awards.json`,
  `practice.json`, `results.jsonl`). The first start of a newer version
  takes them over into the database and then moves them to
  `stats/alt-json/`; nothing is deleted.
- `window_state.json`: window size and all settings, including the language.
- `callsigns.scp`: callsign list (Super Check Partial). It is **not included
  in the repository**. Download the current `MASTER.SCP` from
  [supercheckpartial.com](https://www.supercheckpartial.com) and save it as
  `callsigns.scp` in the data directory. Without the file, the trainer
  generates callsigns from country patterns.
- `woerter.txt`: your own words for the Words tab, one per line, optionally
  with a meaning: `POTA = Parks on the Air`. The “Edit own words” button
  creates the file with instructions and opens it. The words are added to
  the built-in ones.

### Backing up and moving to a new computer

Under “More options → Data”, **Back up …** saves all settings and data
(`stats/`, `window_state.json`, `woerter.txt`, `callsigns.scp`) to a ZIP
file in a place of your choice, e.g. a USB stick. **Restore …** brings
them back on the new computer: `stats/` is replaced completely, the other
files if they are in the backup. The current state is saved first as
`vor-import-<time>.zip` in the data directory. The program then quits;
the restored settings apply from the next start. The database goes into
the backup as a consistent state, even during practice; when restoring,
it is checked first. Backups from version 2.27 and older can still be
restored; the next start takes over their files. The voice for speech
output (`voices/`) is not included, it ships with the AppImage or exe.
