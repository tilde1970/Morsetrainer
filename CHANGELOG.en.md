# Changes

## Unreleased

- **Selectable CW filter:** 2.4 kHz (as before), 500 Hz or 250 Hz around
  your pitch. Signals, noise, QRM and SSB babble pass through it, your own
  sidetone in the contest does not. The narrow filter rings slightly and
  removes noise and distant QRM; the window shows the S/N inside the
  filter, and levels and the award use it.
- **CW QRM close to your frequency:** offset selectable – far
  (300–500 Hz), close (50–200 Hz) or zero beat. With QSB, the QRM now
  fades too, independently of your stations.
- **Strength differences separate from QSB:** how differently loud the
  stations arrive in QSO and contest is now a switch and slider of its
  own, independent of fading. Anyone who had QSB on keeps them; the level
  buttons do not change them.
- **Network: protect your hearing.** Participants can make the
  interference quieter for themselves (10–90 % of the trainer's setting,
  never louder), e.g. with tinnitus or a hearing aid. The trainer sees
  this as ↓ in the table, detail line and CSV.
- **Font size (accessibility):** the whole interface can be enlarged,
  100 % to 200 %, under “More options” or with Ctrl+Plus/Minus/0 in any
  window. Table rows, check boxes and line wrapping grow with it, and so
  does the main window.
- **Announcements for blind and visually impaired users (F9):** the
  program uses its built-in voice to announce results (spelled in Groups,
  Words and Callsigns, errors in Characters), the end of a run, tab
  changes and the daily practice cards; F11 reads out where you are. The
  program waits for the announcement. (German voice.) Without a voice, F9
  and F11 play an error tone. Also in QSO (next
  step, quiz fields, result with the correct values), in Contest (logging
  errors right after the TU, in the audio), in the Statistics tab (F11
  reads an overview) and in tables (selected row).
- **High contrast** (accessibility): black, white and yellow colour
  scheme with strong borders, under “More options”, from the next start.
  All text at least 7:1 against its background, including charts and the
  colours of the QSO stations.
- **Use without a mouse:** buttons and check boxes can be reached with
  Tab, and the keyboard focus is clearly highlighted; Alt+1 … Alt+0 and
  Ctrl+Tab switch tabs, Ctrl+B opens the band conditions, Esc also closes
  the network windows. A mouse click still does not put the focus on
  buttons, so the space bar stays “repeat”. Typing in the notes field no
  longer counts as an answer.
- **“Settings” window** (button top right, Ctrl+Comma): callsign and
  name, language, accessibility and data are now there; “More options”
  keeps only the practice options, so the area above the tabs is half as
  tall.
- A network test depended on the clock and occasionally failed under
  load; it now sets the key times itself.

## 2.37

- **S/N in dB, real levels:** noise is now shown as signal-to-noise ratio
  (S/N in 2.4 kHz) and ranges from +20 dB to −10 dB; if it gets louder,
  the “receiver” turns the signal down (like an AGC) instead of clipping.
  The levels are clearly apart: light +8 dB, medium +2 dB, heavy −4 dB
  (previously +15, +11 and +7.5 dB – hardly a difference for trained
  ears). Chirp is shown in Hz.
- **QSB by level instead of chance:** fading depth follows the slider and
  varies only a little; two overlaid variations make it irregular as on
  the air.
- **Beginners:** switching band conditions on for the first time starts
  with “light”; the window advises learning new characters without
  interference. The manual shows what each level contains.
- **Network:** all participants hear the same fading and the same stations
  (shared random value from the trainer).
- **QRN-proof award:** in Continuous only random characters count – plain
  text is much easier in the noise thanks to context (as with QRQ already).
  Seals already achieved stay.
- After closing the settings window, focus returns, e.g. to the entry
  field of a running session.
- The noise before and after each sequence fades in and out softly
  instead of starting abruptly in the headphones.
- **Fading and QRM keep running:** in Groups, Words, Callsigns and network
  sequences, QSB and the neighbouring QRM restarted at the same point with
  every sequence – each group hit the same part of the fading (possibly
  in the dip for the whole run, or never), and the QRM always sent the same
  opening. Now they keep running during the answer pause, as on the air.
- **Interference no longer distorts the statistics:** runs with band
  conditions no longer count for the character statistics, weighting,
  confusions and review box (they still appear in the history). To keep
  this unambiguous, they can be switched on or off in these tabs only
  between runs; strength and volume still take effect immediately.
- **Band conditions, polish:** the summary under “More options” is no
  longer cut off; interference at 0 % counts as off. The settings window
  stays above the main window and says that on the network the trainer's
  setting applies. The QRN-proof award condition now also states that band
  conditions must stay on for the whole run and must not be made easier.
  In English the award levels are called “conditions light/medium/heavy”
  instead of “band …”, which sounded like a frequency band.
- **Network more robust:** nonsensical band-condition values (NaN,
  infinity) are rejected; prepared interference signals no longer use
  unlimited memory when the trainer changes the setting often.

## 2.36

- **Central band conditions:** which interference, how strong and how
  loud is now set in one place (More options or “Adjust …” in a tab); the
  tabs only switch it on or off. All six kinds of interference (including
  chirp, SSB babble, CW QRM) and the volume are now available everywhere,
  not only in QSO and Contest. Light, medium and heavy remain as quick
  choices and for the QRN-proof award. Old settings are carried over. On
  the network, participants from this version on hear exactly the
  trainer's setting, older ones the nearest level.
- **Reset overall statistics:** the confirmation now says exactly what is
  deleted (statistics per character, review box, confusions) and what is
  kept. Until now it did not mention the review box and still referred to
  log files that no longer exist since 2.28.

## 2.35

- **Award preview:** “Preview: next goal” in the Statistics tab under
  “Awards” shows the award of the next open level, stamped “PREVIEW”,
  without date and number.

## 2.34

- **Banknote-style motifs:** every award has its own motif in the style of
  an intaglio engraving – straight key, racing car, globe, headphones,
  rotary dial, classroom and more. On the right stands the club house of
  the Gütersloh club (N47), where the Morsetrainer is made.
- **Award number:** with a callsign entered, a number such as
  `DL1ABC-KOCH-G-20261004` (callsign, award, level, date) appears at the top
  right.
- **Mac app:** without the unneeded Windows libraries, almost 1 MB smaller.

## 2.33

- **Mac app:** for Macs with Apple silicon (M1 and newer) the release now
  includes `Morsetrainer-macOS.zip`. The app is not signed with Apple; on
  first start you have to approve it, on macOS 15 under “Privacy &
  Security” with “Open Anyway” (see the manual). The data lives in
  `~/Library/Application Support/Morsetrainer/`. There is no automatic
  update on the Mac, only the hint about a new version. Intel Macs run the
  Morsetrainer from source, the manual explains how. Not yet tested on a
  Mac – feedback is welcome.

## 2.32

- **Koch award:** like flow, QRQ, QRN-proof, Rufz and contest, Silver and
  Gold now need two different days. Starting straight at lesson 41 used to
  give all three levels with a single run. Seals already earned stay.
- **Lifeline:** “Koch completed” only appears once lesson 41 is passed
  (gold in the Koch award), not already after one run in lesson 41.
- **Decimal comma:** in German, the statistics table, speed and progress
  now show commas instead of points.
- **Contest:** the selection only shows the name (“CQ WW (zone)”) instead
  of “Contest: Contest: …”.
- **Small things:** heading “Participants” in English, no more empty lines
  in the Groups tab and in the network session box, “History (last 10)” or
  “(last 40)” in all tabs, progress text without a stray line break.
- **Faster start on Linux:** with the ibus input method (default on
  Ubuntu) the main window took about 9 s to build, now under 1 s. The
  Morsetrainer no longer uses an input method; keyboard umlauts still
  work, dead keys and compose sequences do not.
- **Readable drop-down lists:** a drop-down list with keyboard focus showed
  white text on a white field and looked empty – most noticeably the
  contest selection when opening the Contest tab.

## 2.31

- **Safer network:** after 5 wrong PINs a computer is locked for a minute,
  and the trainer sees a notice. Until now the PIN could be guessed in
  seconds.
- **Remove participants:** the trainer can throw a selected participant
  out of the session; that computer cannot get back in until the session
  is closed.
- **More robust:** the trainer limits the number of connections and drops
  computers that flood it with messages; the table is no longer rebuilt
  for every single message.

## 2.30

- **Updates with checksum:** every release contains `SHA256SUMS.txt` with the
  checksums. The update in the program only installs a file that matches;
  a damaged or wrong download is discarded and the program stays as it is.
- **Manual:** the README is now a short overview with pictures; the full
  manual is in `docs/Anleitung.en.md` and, as before, in the program under
  “Help”. New in it: notes on the security of updates and network mode and
  how to verify the checksums by hand.

## 2.29

- **Faster:** statistics, the lifeline and awards are evaluated faster
  after a run; this shows once many runs have piled up over the years.

## 2.28

- **Database:** all practice data now lives in one file
  (`stats/morsetrainer.db`, SQLite) instead of many separate JSON files.
  The end of a run, the overall statistics and the review box are saved
  together, so a crash can no longer leave them out of step. On the first
  start the existing files are taken over and moved to `stats/alt-json/`;
  nothing is deleted.
- **Backing up data:** the database goes into the backup as a consistent
  state, even during practice. When restoring, it is checked first; a
  damaged backup replaces nothing. Older backups can still be restored.

## 2.27

- **Stability:** if audio output in continuous, QSO or contest stops with
  an unexpected error, the session ends with a message instead of staying
  on “running”. If the audio device hangs after Stop (Bluetooth), the old
  run no longer disturbs one started right away. Two program windows on
  one computer no longer write their files through the same temporary
  file. If connecting in the network is cancelled at exactly the wrong
  moment, the connection no longer stays open.

## 2.26

- **Awards only with fast characters:** Worked All Letters and All digits
  count a review box only if it was reached with characters at 18 WPM or
  faster; the review boxes themselves work as before. Boxes from before
  this version still count. “Characters heard” also counts only sessions
  with a character speed of 18 WPM or more.
- **QSO:** the result now also stores the character speed. For Headphones
  and First QSO understood, new QSOs count only from 18 WPM character
  speed, older results as before.
- **Certificate:** for Worked All Letters, QRN-proof and Contest, the award
  shows only the condition of the level reached instead of all levels.
- **Evening summary:** it names only the seals from the daily practice,
  not again those whose window already came today.
- **Club night:** this award only works together in the network. Without
  a seal it is listed last in the overview, with “together in the network”
  instead of “0 / 1 evening”.

## 2.25

- **Prosigns:** in lessons 42–45, passing a run offers the next prosign
  again (AR → KN → SK → BK), as in the lessons before. Prosigns already
  in the review box are included in the daily practice after Koch, so
  they are repeated and do not fade.
- **Network:** a dropped connection (Wi-Fi gone, computer asleep) is now
  noticed after about 15 seconds, even in the middle of a run: trainer and
  participants send each other a regular sign of life. The name is free
  again and the participant can rejoin right away; before, it stayed taken
  for up to a quarter of an hour. From the same computer, rejoining works
  at once, even before the drop has been noticed. With an older version
  on the other side it takes a little longer (about half a minute, while
  nothing is being sent). Overlong answers from the network are cut so
  the trainer window does not freeze.
- **Stability:** if a result cannot be saved (disk full), Rufz, contest and
  QSO still finish their evaluation. Statistics files that were edited by
  hand or damaged no longer make the awards fail after every session.
  Restoring data now also rejects damaged or encrypted ZIP files cleanly,
  before anything is replaced.

## 2.24

- **Club night:** network sessions from versions before 2.22 count again.
  Their logs contain no duration, so since 2.23 they counted as 0 minutes
  and the award was missing. For them, taking part on that day is enough,
  as before.

## 2.23

- **Back up and restore data:** under “More options → Data”, all settings
  and statistics can be saved as a ZIP file to a place of your choice and
  restored on another computer. The current state is backed up
  automatically before restoring. See README, “Backing up and moving to a
  new computer”.
- **Club night with levels, for the trainer too:** the Club night award
  now goes from bronze to platinum (1 / 5 / 15 / 40 evenings). An evening
  counts from 10 minutes of network sessions in total on one day, taken
  part in or led as trainer (only runs with participants). Seals already
  earned are kept. The trainer sees the award window only after “Close
  session”, not in front of the group.
  The trainer's statistics and practice time stay untouched.
- **Lifeline:** on the Statistics tab below the awards, a chart from your
  first practice until today – total stars, highest Koch lesson practised
  and daily speed of the daily practice on a shared time axis, with the
  award seals underneath. The daily speed is now stored for each day for
  this. See README, “Lifeline”.
- **Koch lesson 41 completes the course:** after the 40 lessons of
  lcwo.net, lesson 41 brings no new character, all characters come evenly
  (weak ones still more often); the “Characters” field lists them sorted.
  The prosigns AR, KN, SK and BK are now optional in lessons 42–45; the
  trainer does not move there by itself, neither after a run nor in the
  daily practice. Daily practice counts as “after Koch” after lesson 41
  and then practises without prosigns; a state from the former lessons
  42–45 counts as “after Koch”. Koch Gold is awarded for lesson 41;
  Contest, Headphones and Worked All Contests can be reached from lesson
  41.

## 2.22

- **Daily practice:** a button at the top (or F12) puts together ten
  minutes from whatever is due – warm-up with due characters, main part
  with groups at a fixed speed, wind-down with words, callsigns or
  continuous depending on the lesson – and switches the tabs by itself.
  The next lesson follows without asking on the day after the criterion
  is met; meanwhile the speed only gets slower when needed and faster
  only after Koch, once a day. Three stars a day
  (Showed up, Clean, Ahead), cards between the blocks and an evening
  summary with a comparison to the week before and “5 more min”.
  Afterwards all settings are back as they were. See README, “Daily
  practice”.
- **Week instead of streak:** next to the button you see the week's stars
  per day (days of free practice with ✓) and where you stand on the weekly
  goal of 12 stars; at the start of a week a look back at the last one.
  The streak “X days in a row” in the footer is gone: it dropped to zero
  after a single missed day.
- **Awards:** 17 awards as on the air (Koch, Worked All Letters, QRQ,
  QRN-proof, Rufz, Contest, WPX, Headphones, Endurance …), mostly in the
  levels Bronze, Silver, Gold and some in Platinum. A window shows new
  seals after the exercise (in the daily practice after the evening
  summary); the award can be printed as a certificate with your callsign.
  Overview with progress in the Statistics tab; on the first start
  whatever you have already achieved is filled in. Nothing achieved is
  ever lost. See README, “Awards”.
- **Callsign and name** are now set in one place under “More options”:
  for the awards and as the default in Contest and Network, where they stay
  separate fields (e.g. for a contest callsign). Existing entries are taken
  over. The Contest tab no longer suggests DL4YM as your own call. Without
  a callsign of your own, just enter your name.
- **Daily goal** now defaults to 10 minutes (like the daily practice); a
  goal you already set is kept.
- **Characters, time limit:** the limit now settles where nearly nine out
  of ten characters come in time; before, about every third character was
  “too slow” at any level. A confusion no longer makes the limit longer,
  only a missed character – before, it grew with many confusions until
  there was time to count again. Lower bound 0.5 s instead of 0.4 s –
  below that you would train reaction speed, not recognition.
- **First character no longer clipped:** on Linux the audio system put the
  output device to sleep after a short silence, and the start of the
  first character after starting or pausing was missing (especially with
  Bluetooth headphones). The Morsetrainer now keeps the device awake.

## 2.21

- **Network, typing in paper copies:** after a fixed-pace run the trainer
  enters paper sheets of participants without a computer under “Enter
  paper sheet”. Participants with a computer can choose “copy on paper”
  when connecting and type in their sheet themselves at the end. Scored
  as right/wrong without timing, so not as fluent and not for the speed
  advice. New protocol version: trainer and participants need the same
  program version.
- **Print answer sheet:** with the fixed pace the trainer opens a
  numbered sheet for printing in the browser, with one box per character
  for groups.
- **Error log:** unexpected program errors now go to `fehler.log` in the
  data folder, and the program says once where the file is. Before, the
  exe and AppImage simply did nothing on such an error.
- **More robust:** a broken download no longer leaves the update hanging,
  an error during MP3 export no longer locks the Speak tab, and the window
  closes even if saving fails.
- **Speak:** 2 is now said “Zwo” as on the air, and Echo sounds like
  “Ekko” instead of with a German ch.
- **More honest character statistics:** words, plain text in Continuous,
  QSO copying and plain text on the network no longer count for the
  character statistics, the weighting and the review box, because the
  context gives many characters away. They still appear in the history.
  When copying a QSO, characters guessed ahead (“DE”, “599”) no longer
  count as correct.
- **Groups, Words, Callsigns:** after an error the solution now comes
  right away, shown and played, then the next sequence, as when copying on
  the air. Up to 3 failed attempts can be set; “never” is gone. A
  character recognised only after repeating counts as not recognised, as
  with single characters.
- **Character speed too slow:** below 18 WPM the header now points out in
  every tab that the characters can be counted and offers Koch speed; so
  does the next-lesson dialog. “Speed adapts” stretches the characters
  only down to 18 WPM (before: 15), below that the gaps get longer.
- **Continuous:** band conditions (light, medium, heavy) run under the
  whole session.
- **Practise due characters:** missing due characters are added for one
  session only, then the lesson's character set applies again.

## 2.20

- **Speak:** the spelling alphabet now sounds right. The German voice read
  the English words the German way, e.g. “Mike” as “Micke” and “Zulu” as
  “Tsulu”; now it says them as intended.

## 2.19

- **Network, continuous:** band conditions now lie under the whole run.
  Before, only VVV = and + were noisy, not the groups in between.

## 2.18

- **Network:** new flow “Continuous”: groups without pauses for a set
  duration, everyone types along continuously, without Enter. Scored at
  the end as in the Continuous tab and reported to the trainer per group
  (table, solutions, CSV). New protocol version: participants need the
  same version as the trainer (the update is offered).
- **Network:** QSO plain text comes in sections up to the next =, K or
  closing sign (e.g. “UR RST 599 599 =”) instead of word by word, and the
  number counts whole QSOs (default 1). Before, it stopped after as many
  words as sequences were set.

## 2.17

- **Network:** no more Enter needed – as soon as you have typed as many
  characters as were sent, the answer is done (during the tone it is
  scored afterwards, as before). Enter only if you have fewer; the last
  keystroke counts as the answer time.

## 2.16

- **Updates:** on start the Morsetrainer checks whether there is a newer
  version and offers to download it and restart (exe or AppImage, from
  GitHub). Without internet it stays quiet; “No” applies to this version,
  after that there is just a hint in the footer.
- **Network:** if the trainer has a newer version, the participant is asked
  on connecting whether to download it; after the restart it connects again
  by itself. Works from the next update on – anyone still on 2.15 or older
  downloads 2.16 by hand once.

## 2.15

- **Network:** the start sign VVV = comes before the first sequence and the
  end sign + after the last one – as in the other tabs, also under the band
  conditions and over the trainer's speakers. Can be switched off under
  “Send start and end signs”.

## 2.14

- **New “Network” tab: practising as a group.** A trainer opens a session
  on the local network (with a PIN), participants find it with “Search” and
  join with their name or callsign. Everyone hears the same sequence –
  characters, groups, words, callsigns or your own text – on their own
  headphones and copies it. The trainer sees live who typed what, plus the
  group's accuracy, most common errors and weakest characters, and can save
  everything as CSV. Only text is sent; each computer generates the sound
  itself.
- Scored honestly as in the other tabs: a correct answer only counts as
  **fluent** on the first hearing and within the usual time window; after
  “Repeat for everyone” or when too slow it is correct but uncertain.
  Anyone who was not fluently correct hears the solution again. Phrases and
  QSO plain text can be sent too; a slow character speed prompts a hint
  towards Koch speed.
- For the trainer: clicking a participant shows their errors and weakest
  characters; a speed recommendation (faster from 90 % fluent, slower
  below 75 %) can be applied with a button. The CSV contains speed, time to
  Enter and repeats per sequence plus errors and weak characters per
  participant. F5 start/stop, F6 repeat for everyone, F7 next.
- The participant table grows (up to 12 rows, then a scroll bar) and can be
  moved into a separate window.
- **Fixed pace for copying on paper:** the next sequence comes after the
  tone plus a writing pause (the same for every sequence, default by
  content), whoever has answered. Until the end the trainer's screen gives
  no solution away; participants at a computer only see “No. 7 noted” and
  at the end the whole list to listen to.
- **Solutions** in a separate window for the projector: the current number
  during the run, afterwards all solutions numbered in several columns,
  larger/smaller font, copy; a click plays a solution again.
- **Sound for everyone from the speakers:** optionally only the trainer's
  computer plays and participants type on a silent computer – no
  headphones and no offset between computers. At a fixed pace the
  trainer's computer plays along anyway, for everyone copying on paper.
- **Continuous:** the whole evaluation of a session can be shown in a
  separate window, split into groups (without groups in blocks of 5),
  errors in red, with font size, copy and “Sent text only”. Previously only
  the last 30 characters were visible.
- Band conditions now also run under the start and end signs (VVV =, +):
  the interference is there from the start.
- The network protocol is now version 2: trainer and participants need the
  same program version.
- The window is now at least 720 pixels wide so that all tabs stay
  readable.

## 2.13

- **New “Speak” tab (listen & say):** practise without a keyboard, like
  Morse Code Ninja. After the Morse code you say out loud what you heard;
  then a voice (Piper, offline) announces the solution and the code comes
  once more. For characters, groups, words, phrases and callsigns;
  characters and callsigns are spelled, words and phrases announced as a
  whole or with their meaning. The voice is German.
- **Save as MP3:** the same exercise as a file for your phone or the car.
- **Plain text in the Continuous tab:** besides random characters also
  words, QSO phrases (“TNX FER CALL”, “UR RST 599”), callsigns or complete
  QSOs in one go.
- **Spaced repetition (review over days):** characters recognised reliably
  and quickly come back after 1, 2, 4, 8, 16 and 32 days, uncertain ones the
  next day. Decided once a day from 5 attempts; only random characters
  promote a character, because in words and plain text the context helps.
  With “weak favoured”, due characters come up more often; in the Statistics
  tab you can practise them specifically.
- **Characters per minute:** next to the WPM fields the speed is also shown
  in CPM (≈ 5 × WPM by the PARIS standard). The statistics additionally show
  the characters per minute actually achieved, measured from the correctly
  recognised characters and the time they took.
- **English:** the user interface is now also available in English, switch
  under “▸ More options” → “Sprache / Language” (takes effect after a
  restart). Help, meanings of the abbreviations and the head-copy questions
  are translated too; the voice in the “Speak” tab stays German.

## 2.12

- **Program icon:** window, taskbar and the Windows exe now show the same
  icon as Gear Lever (blue with dot, dash and “CW”).

## 2.11

- **Help in the program:** the “Help” button in the footer shows these
  changes and the manual (README).
- **Uncertain answers:** the assumed latency for correct but uncertain
  characters (after repeat or too slow) no longer feeds into the usual value
  it is measured against. Otherwise the yardstick rose with every session,
  especially with “Listen first”.

## 2.10

- Correct but uncertain characters count with twice the usual latency (at
  most 5 s) instead of a flat 5 s. They come up more often without
  overdoing the weighting. In the Callsigns tab the callsign character set
  is used for this.

## 2.9

- **RufZ run** in the Callsigns tab (modelled on RufzXP): 50 callsigns, one
  attempt each, the speed grows, score = length × effective speed, best
  score with starting speed and history.
- **Replay missed callsigns** after the RufZ run, including those recognised
  too slowly: first just listen, then again with the solution and your
  input, at the original speed. F6 again, F7 from the start, Esc stop.
- **Words:** “Listen first” is the default (existing settings are switched
  once). New abbreviations such as DX, CU, RPRT, UFB, DOK, SN, BN, WKG, plus
  R, K and the prosigns KN and SK. A weak character comes up more often, but
  in changing words.
- **Time window visible:** after the tone it says how quickly the answer
  should come; answers that are too slow are noted.
- **QSO:** new evaluation “Head copy + questions” with content questions
  (name, QTH, rig, weather … or exchange); pile-ups adjustable, default
  “Short” with estimated duration.
- **Characters:** feedback with your own time and the limit; after a
  confusion the correction plays correct – typed – correct.
- **Statistics:** confusions of the last 30 days.
- **Continuous:** comparison after stopping, F5 starts and stops, Esc stops.
- **Contest:** “?” in the call field asks back (DL1?, DL?ABC), summary by
  type of error, speed and pitch spread of the callers adjustable, F10
  starts and ends.

## 2.8

- **Honest measurements in all tabs:** only the first attempt goes into the
  statistics; for the Koch lesson it only counts without repeat and within
  the time window. Head copy is self-assessed and does not count.
- **One speed rule:** the effective speed is adjusted, first via the
  Farnsworth gaps, then via the character speed (not below 15 WPM).
- **Callsigns:** by default only from learned characters, suffixes like /P
  rarer and more realistic.
- **Words:** only from 10 matching words, words with the newest Koch
  character favoured.
- **Continuous:** characters in groups with a word gap.
- **Contest:** callers also answer to an almost correct call; if unnoticed,
  “Busted” appears in the log.

## 2.7

- Fixed: in Groups, Words and Callsigns the session stopped after a correct
  answer since 2.5.

## 2.6

- AppImage with embedded update information, so programs like Gear Lever
  find new versions.

## 2.5

- Koch lessons 41–44: the prosigns AR, KN, SK and BK.
- After 90 % in Characters, switching to Groups is offered.
- Typos no longer end up in the confusion drill.

## 2.4

- Characters: time limit on by default; a wrong character is played with the
  solution and asked again only after a few others.
- The space bar no longer stops the session by accident.

## 2.3

- New, compact interface with its own design, all tabs built the same way.
- Slider for the volume of the noise.
- Meanings of QRL, CUAGN and NR added.

## 2.2

- **Koch learning path:** lessons with promotion at 90 %, listen to the new
  character, Koch speed 20/10.
- **New Words tab** with meanings and your own words (woerter.txt).
- Input modes Copy while listening, Listen first and Head copy; error
  positions marked.
- Group length and speed can grow; band conditions in three levels.
- Characters with an adaptive time limit, practise confusions specifically,
  daily goal with streak.
- More robust: data files are written safely, audio output errors end the
  session with a message.

## 2.1

- The space bar repeats in Characters, Groups and Callsigns.

## 2.0

- First version: Characters, Groups, Callsigns, Continuous, QSO with
  pile-up and band conditions, Contest as running station (similar to Morse
  Runner), statistics with confusions and progress history.
- Ready-to-run programs as AppImage (Linux) and exe (Windows).
