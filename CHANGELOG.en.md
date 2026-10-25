# Changes

## 2.67

- **Statistics, insights:** New section “Insights (last 90 days)” with its own
  button in the jump row. It shows the lag when copying in “Non-stop” (it
  fills up only with practice), the error types per week (mixed up, swapped,
  not recognised), fading within a run, the confusion pairs over time, the
  error rate per character and characters that have fallen back in the review
  box. A verdict such as “more often” or “fading” appears only if it stands
  out from chance; otherwise it says “no reliable difference”, with the number
  of cases in brackets. Two buttons practise the displayed pairs and the
  unrecognised characters. “Read the insights aloud” and F11 read everything
  out.
- **Statistics, comparison line:** Accuracy is now also shown per mode (“By
  mode: One by one 81 % → 81 %, Non-stop 78 % → 87 %”), because the average
  depends on which modes you practised. “Before (N days)” names the days
  actually covered. Repeat questions and characters without timing no longer
  count there.
- **Statistics, time of day:** The line from 2.66 is gone again; it showed no
  difference with the data at hand.
- **Confusions:** The button for targeted practice says why nothing happens
  when there are too few confusions, and names the characters after the switch.
- **Guide and interface:** The guide has been rewritten and is about 30 %
  shorter; the English version has been reworded. In the English interface the
  band-conditions preview is now called “Preview”, plus consistent spellings.
- **Internal:** Lines from “Non-stop” store the lag in characters; tests for
  the insights.

## 2.66

- **Statistics, time of day:** A new line below the comparison shows accuracy
  by time of day (morning, midday, afternoon, evening, night) and when you do
  best. Daily practice and free practice count together; a time slot counts
  from 5 sessions, and with less than 3 points between them it says “Hardly
  any difference”. Tempo and mode are not factored out.
- **Practice tab, lesson 41:** The line next to the “Lesson” field now points
  out that the prosigns follow from lesson 42.

## 2.65

- **Documentation:** The development guide and the change lists have been
  tidied up. The program itself does not change.

## 2.64

- **Statistics, jump row:** Jumping with the keyboard or a screen reader now
  really lands in the section: the focus moves along, the section is announced
  (“Section Review box.”), and the next Tab key no longer scrolls back.
  “▲ Back to top” leads back to the jump row; for speech output the buttons
  are named “Back to the jump row”.
- **Practice tab, lesson 1:** The line next to the “Lesson” field shows
  “new: K, M” for lesson 1, and “▶ listen” plays both characters (before: only
  M).
- **Internal:** More tests cover the 14-day break threshold and the rated power
  of the rigs.
## 2.63

- **Statistics:** The tab has become long. At the top there is now a “Jump to”
  row with equally wide buttons (week, awards, lifeline, review box,
  confusions, progress); each section has a “▲ Back to top” button at the
  bottom. With an empty account the character table is only four rows high.
- **Daily practice:** The button that ends the practice in the tab now has the
  same label as the one in the bar (“End daily practice (Esc)”) and is no
  longer blue; blue stays for start. After at least 14 days off, the card after
  the warm-up says how many characters that used to be solid were right back.
- **QSO:** Rig and power fit together: an FT817, IC705, KX2 or KX3 never sends
  more than its rated power; 400 and 750 W only come with the other rigs.
- **Manual:** README and manual (German and English) mention the possible
  false alarm of an antivirus program for the unsigned Windows file and that
  the Linux package exists only for 64-bit PCs (x86_64); on ARM devices such as
  the Raspberry Pi, run from the source code. The US zones in the exchange are
  still rounded (W4 gives zone 5), now with an example. The Ko-fi button is an
  image in the README.
## 2.62

A full review of the whole software (code, data, tests, signals, performance,
subject matter, platforms, usability, accessibility, didactics, participant
view, error analysis, motivation, documentation). The main changes:

- **Daily practice, getting started:** On the very first day in lesson 1 a card
  plays K and M before the time limit starts. Before the first daily practice
  the bar says how to begin and where to find “Returning to CW”; after at
  least 14 days off the bar welcomes you back.
- **Relaxed daily practice:** New tick box under “Settings …” (card
  “Practice”): the warm-up runs without a time limit and does not count for
  the review box and the awards that depend on it. If many characters were too
  slow, the in-between card points this out.
- **Review box:** A character is decided only from 8 attempts a day (before:
  5). If the share of fluent hits is between 80 and 90 %, a character stays
  where it is. With many due characters the warm-up gets longer (up to 4
  minutes), and the in-between card says for how many attempts are still
  missing. The gaps get shorter already in the Koch part once it sits.
- **Evening summary and in-between card:** The evening summary names tomorrow's
  speed with the reason and, after about ten practice days at the same speed
  and in the same lesson, once says that plateaus are normal in listening.
  While the comparison with the previous week is still missing, it shows
  today's counters. From 4 mistakes the in-between card says what caused them
  (“of 9 mistakes, 5 were mix-ups (B for 6 three times), 3 too slow, 1
  missed”), with at most one tip. Stopping without a star no longer says “your
  stars stay”.
- **Weekly goal:** 8 instead of 12 stars; in the developer's data the weeks
  were at 2 to 6 stars, only one reached 12.
- **Error analysis:** Every mistake has a cause (heard, too slow, only after
  repeating, missed, swapped); only another character counts as a confusion,
  also for the award. The column “Confused with” names the causes. The repeat
  after a mistake comes after 4 to 8 characters and does not count for the
  overall statistics and the review box. The confusion list shows pairs only
  from 3 cases and marks pairs that do not sound alike as “typo?”; the button
  for targeted practice takes only similar pairs, switches on “weak favoured”
  and restores the character set afterwards. The character table is sorted by
  error rate.
- **Weighting:** “Weak favoured” looks at the last 14 days: a character that
  slips now stands out; characters often confused with a weak one come up more
  often; latency follows the last days. In the One by one tab the same
  character never comes twice in a row (from five characters).
- **Operation:** Hints per content and input style in the One by one tab, the
  start button sits above the options, number fields take the value when you
  leave them and announce a correction. “Delete statistics” asks with Enter =
  Cancel. Ctrl+Q quits the program (in the daily practice only on the second
  press), Ctrl+F1 opens the help in the Contest too.
- **Accessibility:** After switching tabs the focus is on a visible spot,
  locked tabs explain themselves, input style and corrections are announced,
  the fields in the Contest have names, and several contrasts (high contrast,
  light theme) are better.
- **Signals:** Crashes (QRN, thunderstorm, electric fence) are no longer pumped
  by the AGC; interference fades in and out softly; the noise ceiling applies
  behind the filter; the QSB strength can be set up to 100 %; “no noise” at
  0 %.
- **Subject matter:** Frequencies lie only in the CW segments of the IARU band
  plan, numbers include short numbers (5NN, T for 0), the zones of island
  territories are right, the IARU HQ list follows the 2025 results, QRL and NIL
  are more exact, /QRP is no longer a suffix.
- **Data:** Crashed runs are added afterwards, good backups are not pushed out
  by empty ones, rescue files stay, a second window blocks importing a backup,
  a locked or too new database is reported at start, read errors overwrite
  nothing, and a wrong clock is detected.
- **Installation:** If Tk or PortAudio is missing, the start says what to
  install; “No sound?” in the manual helps step by step, and the error messages
  point to it. The packages have upper limits, Python 3.14 is tested too.
- **Fixed:** Network polling loops that kept running, wrongly typed settings
  that prevented the start, and in the Characters tab absence counted as a
  mistake.
- **Manual and picture:** README and manual (German and English) are brought up
  to date; the picture of the main window shows the current state.

## 2.61

- **Statistics:** The reaction time in the comparison line is now the median,
  like in the character table below it. A few very long answers no longer pull
  the value up.
- **Message windows at large font sizes:** Messages such as the notice about
  your data at start-up are never wider than the screen at 200 % font size.

## 2.60

- **Tables at large font sizes:** Below a shortened table, a line says which
  rows are visible (“Rows 1 to 4 of 15, more with arrow down”); when all rows
  fit, the line is not shown. The tables on the network (participants,
  results) are shortened at large font sizes as well, and changing the font
  size no longer resets their height.
- **Table announcements:** When you Tab into a table, the announcement now
  also gives the number of rows (“15 rows, arrow keys choose a row”). The
  character table in the statistics is called “Characters sorted by errors”
  instead of taking the name of the long comparison line above it; the stray
  period before the comma in table names is gone.
- **File paths in announcements:** Error messages (error window, red status
  messages) read the whole path, with pauses between the parts; before, only
  the last name of an unreachable folder was heard. Other messages still give
  only the last part. Folders with spaces (“Application Support”) and a
  trailing slash are handled correctly. The voice says “and/or” as “and or”.
- **Statistics:** In “New:” the letters come before digits and special
  characters; anything beyond six is “and 2 more”.
- **Callsigns tab:** During a run the affixes (/P, guest prefixes) follow the
  character set from the start, not the “Zeichen” field.
- **Restoring data:** The question now names the file `vor-import-….zip` in
  the data folder, where the current state is backed up first.
- **Guide:** New characters in the comparison line, shortened tables, file
  paths in announcements and the fixed callsign choice during a run are
  described.

## 2.59

- **Statistics:** The comparison line names characters that only appeared in
  the last 7 days and reminds you that new characters slow the average down
  at first. F11 says only the sentence, without the characters.
- **Tables:** At large font sizes they show fewer rows (at least 4) so they do
  not grow taller than the screen; the other rows scroll. When you Tab into a
  table, the announcement gives name, role and first row together instead of
  the row replacing the name.
- **Announcements:** The voice reads file paths with their last part only
  (“fehler.log” instead of every folder before it).
- **Callsigns:** During a run the choice of callsigns stays fixed, even if you
  change the “Zeichen” field at the top; it applies after the run. In a Rufz
  run, made-up callsigns could otherwise slip in. For made-up callsigns the
  saved session now also names “learned characters only” and the character
  set.
- **Certificates:** An empty certificate file no longer counts as usable; the
  fallback to the system's certificates then applies (callsign list, update
  check).
- **GitHub:** Sponsor button and a note at the top of the README (Ko-fi).

## 2.58

- **Automatic backup:** On exit, Morsetrainer makes a backup by itself at most
  every 7 days in the folder `auto-sicherung/` of the data folder; the last 4
  are kept. Switch it off under “Settings … → Data → Back up automatically”.
  Restore with “Restore …”. If the backup fails, the next start says so (note
  file `auto-sicherung-fehler.txt`).
- **Notices at start:** Besides data from a newer version, the start now also
  reports when the data format update failed or a damaged database was set
  aside. The texts are shorter and name the next step; they are always
  spoken. “What's new”, the award catch-up and the update offer wait until the
  notice is closed. Warnings and errors carry a symbol (⚠, ✖) before the text.
- **Database:** The journal of a damaged file is kept even without hard links
  (FAT, some network shares), as are the rollback journal in network-drive mode
  and an orphaned `-wal`. Two set-asides within the same second no longer
  overwrite each other. Windows long paths (`\\?\C:\…`) are not taken for
  network drives; the macOS detection copes with “ on ” in the device name.
- **Band conditions, answer pause:** The noise in the answer pause (Groups,
  Words, Callsigns) stays as loud as at the end of the sequence instead of
  dropping by up to 12 dB.
- **Statistics:** The comparison of the last days counts only completed runs.
  F11 reads it in a shorter form (without the character count of the earlier
  period and without the hint).
- **Callsigns tab:** The button is called “Liste aktualisieren”.
- **Manual:** The data folder section is structured (notices at start, restore
  a backup, automatic backup, restore data by hand, delete all data). New:
  stars in the announcements, volume with a narrow CW filter.

## 2.57

- **Data from a newer version:** If the data comes from a newer version of
  Morsetrainer, a notice at start says that statistics, awards and the daily
  practice are therefore empty and nothing is saved. It is spoken even with
  the announcer off; at the very first start the greeting follows only after
  it. The data stays unchanged.
- **Database, format change:** An older database is raised to the new format
  step by step. A checked copy `morsetrainer.db.vor-v<number>` is left
  behind first. If a step fails, the file stays untouched and is not set
  aside as “defekt”; a second window does not run a step twice.
- **Database, network drives:** If the data folder is on a network drive, the
  database uses the classic journal instead of WAL. On Linux `vboxsf`,
  `virtiofs` and GVfs shares are now recognised too, on macOS SMB, NFS and
  AFP. If the `mount` command hangs there, startup does not stall.
- **Damaged database:** Its journal (`-wal`) is set aside with it
  (`….defekt-<time>-wal`) instead of being lost. The data backup includes
  neither `.defekt-*` nor `.vor-v*`, and the database is merged when closing.
- **Manual:** It explains how to bring a set-aside database back by hand and
  which helper files may be deleted.

## 2.56

- **Statistics, comparison:** The comparison line says how many characters
  each period is based on (“Before (30 days): … (from 412 characters) · Last
  7 days: …”). A period appears only from 10 characters, otherwise it reads
  “too few characters (3 of 10)”. It never shows “100 %” while there were
  errors. “Smaller is faster” sits on the line, and a note explains that
  new characters make the average slower at first.
- **F11 in the Statistics tab is shorter:** The comparison comes right after
  the overall result, and the week is one sentence (“practised on 3 of 4
  days, today still open”) instead of every day separately.
- **Small screens:** The header collapses to one line not only from 200 %
  but earlier, when the window would otherwise be taller than the screen.
  A remembered open header opens only if there is room. The start window is
  never larger than the screen. When you enlarge the font and the header
  collapses, the announcement says “Header collapsed.”.
- **Tables:** The selected row scrolls into view, in the table and on the
  page. If columns are hidden, the announcement says that left and right
  arrow show more columns.
- **Announcements and display:** “Header” and “More options” say “expanded”
  and “collapsed”, the data folder “is being opened”. The speed in the
  statistics wraps at large font sizes instead of being cut off. The
  scroll bar thumb is more subtle in the normal theme, its arrows are easy to
  read.

## 2.55

- **Returning to CW:** Under “More options” there is a new tick box
  **Returning to CW** for everyone who used to know CW. The daily practice
  then moves up faster: three lessons at 95 % or more on the first try, one
  from 85 %, and – if no speed is saved yet – starts at 15 WPM without
  Farnsworth. The evening summary shows how many of the 41 characters you
  have regained.
- **Numbers:** The Non-stop tab has a new content **Numbers**: signal
  reports, CQ zones, serial numbers, frequencies, power, times and years,
  only from the digits you have learned. After stopping, a line explains
  what the last numbers were. Like plain text they do not count for the
  lesson.
- **“High-Speed” award:** plain text at top speed: Non-stop with phrases or
  QSO plain text at 25, 30, 35 and 40 WPM, from lesson 40, full 3-minute
  run, no Farnsworth, at least 90 % correct. Silver and above on two days.
  The motif shows a speedometer with a rocket.
- **Dupes in the contest:** Once D, U and P are learned, a station that is
  already in the log sometimes calls again in a contest run in the QSO tab.
  The running station says “DUP”, and that is not a new QSO: it does not go
  into the log. “Head copy + questions” asks about it.
- **More varied QSOs:** more CQ calls in the contest (“CQ CQ TEST DE …”,
  in CQ WW and WPX also “CQ DX TEST …”), and in a normal QSO someone
  sometimes calls “CQ CQ DX”. Some stations carry /P or /M after their
  callsign, but only once the slash is among your learned characters
  (header).

## 2.54

- **Stations from your part of the world:** The settings have a new
  **Locator** field under “Station” (Maidenhead, four or six characters,
  e.g. JO41). The stations generated in QSO and Contest now come from where
  you sit: from Japan you hear more of Asia and North America, from
  Germany more of Europe, always with the best band conditions. Without a
  locator the country of your callsign counts; an invalid locator is named
  below the field. This applies with and without a callsign list.
- **Country list from 19 to 78 countries:** new are, among others, Canada,
  Mexico, the Caribbean, South America, Asia, Africa, Israel, Turkey, the
  Balkans and the Baltic states. Prefixes, CQ and ITU zones, names and
  places were corrected after a technical review. Austria, Australia and
  Canada name places that fit the digit in the callsign (OE1 Vienna, OE8
  Carinthia …), Canada its province in ARRL DX. Hawaii, Alaska, Puerto
  Rico and Guam count as DX in ARRL DX (report plus power) and no longer
  as USA.
- **Zones by digit:** CQ and ITU zone depend on the digit in the callsign
  in the USA, Canada, Russia (Kaliningrad, Siberia) and Australia; the US
  territories have zones of their own.

## 2.53

- **Callsign list at the push of a button:** In the One by one tab, content
  Callsigns, “Load callsign list (supercheckpartial.com)” downloads the
  current MASTER.SCP straight from the source; once a list is there, the
  button reads “Update callsign list”. Not during an exercise; if one is
  started while loading, the new list applies after it ends. If something
  goes wrong, the old list stays, and the message says in words what
  happened (no connection, server not responding, Wi-Fi login page …) and
  how to save the list by hand.
- **Secure connections on Mac and Linux:** The Mac app and the AppImage now
  find the system certificates, also on Fedora, Arch and openSUSE. The
  callsign list and the new-version notice now work there.
- **Statistics: are you getting better?** Below the total you see how the
  last 7 days went against the 30 days before: “Last 7 days: reaction
  0.48 s, 92 % correct · the 30 days before: reaction 0.61 s, 88 %
  correct”. The character table also shows “before → now (s)” per
  character (median, only from 20 measurements on each side). The
  reaction comes only from the One by one tab, content Characters, so the
  comparison stays honest; the accuracy counts all exercises. There is
  also a new “This week” box with the week strip and the weekly goal. F11
  reads it all.
- **F11 during the time limit:** Pressing F11 during the deadline no longer
  costs answer time: the character does not count now, the limit stays,
  and it comes again later unannounced. Without the time limit the answer
  after F11 still counts as right or wrong, but without time: speed,
  reaction and the review box stay untouched.
- **Shortcuts never count as an answer:** Ctrl+Plus, Ctrl+0 or Ctrl+comma
  in the middle of an exercise counted as a wrong answer in the One by one
  tab.
- **F11 in Contest:** spells what is in the Call or Exchange field (Call in
  the phonetic alphabet, an empty field as “empty”).
- **Large font (200 %):**
  - The header is collapsed to one line, such as “▸ Koch lesson 3 ·
    20/10 WPM · 600 Hz · KMUR”; click or Enter opens it. “Settings …
    (Ctrl+,)” stays within reach on the right.
  - The daily practice bar shows only the weekly goal. This way the
    exercise and its Start button fit even on small screens.
  - The settings window fits on the screen: the content scrolls, “Close”
    stays at the bottom, and hints move below the fields when space is
    short.
  - Hint texts are no longer cut off on the right.
  - Tables grow with the font; if they do not fit, they scroll sideways
    (scroll bar, left and right arrow keys).
  - After each answer, One by one and Groups scroll to the feedback.
  - The header remembers whether it was open when you quit; the week strip
    is in the Statistics tab; the footer is shorter.
  - The focus frame on flat buttons (“Help”, “Settings …”) is easy to see.
  - Ctrl+Plus and Ctrl+Minus announce the new size, but never in the middle
    of a long Morse tone.
- **Callsigns:** Too few real callsigns from your learned characters (under
  30, under 50 in a RufZ run) no longer block the start; the trainer makes
  up matching ones, and the hint above the load button says so. This does
  not apply with a prefix filter. RufZ runs with made-up callsigns count
  towards the diploma. Without a list it now reads “No callsign list yet –
  callsigns are made up from patterns.”
- **Open data folder:** Under “Settings … → Data” a button shows the data
  folder in the file manager, for example to save a callsign list by hand.
- **Weekly goal:** Your own count comes first (“7 ★ this week, goal 12”),
  so 12 does not look like a limit.
- **Prepared for Tk 9.1:** Disabling, state and announcements also work
  when Tk builds classic instead of themed controls while a screen reader
  is running.
- **Self-test:** The release builds now also check that secure connections
  find certificates.
- **Manual:** Loading the callsign list, header at 200 %, F11 during the
  time limit and in Contest, statistics comparison, data folder; the step
  from “medium” to “heavy” in band conditions is explained more
  precisely.

## 2.52

- **Announcements (F9, F11):**
  - F11 no longer cuts off a Morse tone: the announcement waits until the
    current character or correction has finished.
  - F11 spells characters in the feedback (“Wrong: was period, you:
    separator”) instead of swallowing punctuation, no longer reads doubled
    punctuation, nor “Your answer?” once the answer is given.
  - F9 and F11 also work while a drop-down list is open; F11 then names
    the highlighted entry, Esc says “List closed.” and the value that stays.
- **Help:** the help text can be reached again with Tab after leaving it
  and announces the paragraph at the reading position; Tab out of the text
  says where the focus lands; F1 in the help window jumps back into the
  text. The buttons at the bottom follow the visible order when tabbing.
- **Windows announce the focus when they open:** the band window names the
  “light” level, settings open in the call sign field.
- **Greeting on first start:** also names the daily practice key. With a
  screen reader running it suggests muting it while practising and comes a
  little later, so it does not talk over the screen reader's own window
  announcement.
- **Band window:** says that QSB and flutter get harder up to 80 % and that
  runs with band conditions count for practice time and awards, only not
  for the character statistics (also via F11). The footer explicitly refers
  to listening to a sample.
- **Band level:** if you make the band easier during the band outro of the
  daily practice, a good result no longer cancels an earlier miss; a failed
  run still counts towards falling back.
- **Interface and contrast:**
  - Selected text in fields without focus keeps the program's colours
    (previously white on grey, hard to read).
  - Number and unit (“400 Hz”, “100 %”) are no longer split across lines in
    hints; the pitch field is visibly labelled “Pitch”.
  - Speech rate and volume of the spoken feedback are indented under
    “Announce feedback”, with the note “100 % is normal”.
  - Above the lifeline, once there are days, a hint explains how to go
    through the days by keyboard; the announcement also mentions Page Up/Down.
- **Guide:** greeting with F12, muting VoiceOver for good, and how to find
  the screen reader paragraph in the help.

## 2.51

- **New English voice:** announcements with the English interface now use
  the LJ Speech voice instead of Lessac. Lessac is based on a dataset
  licensed for research only; LJ Speech is in the public domain. If you
  run from source, fetch it with `bash packaging/get_voice.sh`; until then
  the old voice keeps speaking.
- **Licenses:** the help has a “Licenses” tab with the licenses of all
  components. The program files contain Piper and espeak-ng
  (GPL-3.0-or-later) and are therefore licensed as a whole under the GPL;
  the Morsetrainer source stays MIT. The source archives of piper,
  espeak-ng, lameenc and LAME are attached to the release.
- **Feedback on the band level:** if the band conditions wind-down of the
  daily practice changes the level, the evening summary says so (“90 %
  twice – next band conditions wind-down: medium” or “Twice in a row below
  80 % – next band conditions wind-down back to light”). The first step up
  to “medium” earns ★ Ahead.
- **Plain words revised:** common QSO words added (BY, DO, THEIR,
  WHICH, SINCE, AROUND, HOMEBREW, INVERTED, MILES, TEST, OK …), some rare
  weather and landscape words removed. The roughly 120 most common words
  come twice as often.
- **Band level counted more fairly:** for stepping up and back only the
  first complete band conditions wind-down of a day counts; stopped ones
  do not, and two on the same day are no longer “twice in a row”. Strength
  differences are off in the wind-down (with one station they are only a
  random penalty); afterwards your own setting applies again.
- **Non-stop varies per group or word:** with “Vary pitch and speed
  slightly”, Non-stop now gives each group or word its own pitch and speed
  instead of one for the whole run. The CW filter follows the pitch.
- **Awards show the state of every level:** a selected row shows for each
  level whether it is achieved (with the day), how far you are (e.g.
  “Silver from 25 lessons: 18 / 25”), whether only the second day is
  missing, or “not yet”.
- **More spoken feedback:**
  - In the QSO log check the fields say what is entered when you move
    into them (or “Empty.”); typing is spelled out once the QSO is over.
  - F6 says why “Again” is locked (in the daily practice, and in head
    copy before checking).
  - In the daily practice F11 names the mode, with the level for the band
    conditions wind-down; the contest wind-down names the contest.
  - Before a run in One by one with Words, F11 also reads the count line (how many
    words or phrases fit).
  - With phrases the announcement explains the two-part time window once
    per run – before the first tone.
  - In the band conditions wind-down the Band conditions window says that
    the daily practice set the level; the announcement before the block
    mentions an own CW filter that was set back.

## 2.50

- **Daily practice after Koch with a changing wind-down:** after lesson 41
  the wind-down (4 min) changes from one practice day to the next:
  callsigns, a short **QSO for head copy** with questions, callsigns
  again, then a short **contest run to log**. The QSO only comes once the
  prosigns AR, KN, SK and BK are learned and it fits into the four minutes
  with its questions (roughly from 18 WPM effective); otherwise callsigns.
  The block ends with “Check”; the daily practice stays at ten minutes.
  After the QSO the announcement says how many questions there are, which
  field comes first and that F8 checks; afterwards the QSO tab is back to
  normal.
- **Wind-down under band conditions:** from 15 WPM effective, every second
  cycle brings non-stop under band conditions instead of the contest run:
  first “light”, after two days with 90 % or more “medium”, after twice in
  a row below 80 % back to “light”. The wide filter and at most 100 %
  noise volume are used; if you have turned the volume down, it stays
  that way (it then does not count for QRN-proof). Afterwards your own
  band settings are back.
- **Wind-down by practice days:** it now changes by the number of days
  you practised, not by the calendar. Whoever practised every other day
  used to get the same one every time.
- **Hint on the prosigns:** once the daily practice has passed lesson 41,
  the evening summary mentions AR, KN, SK and BK (lessons 42–45) once,
  with a button “Set lesson 42”.
- **Words tab with type: Abbreviations / Plain words / Phrases / mixed.**
  “Abbreviations” is the previous word list. **Plain words** brings about
  300 English QSO words written out (WEATHER, STATION, THANKS …; from
  lesson 10, before that there would be too few), also in
  Non-stop, Speak and network; there “Words” is now called
  “Abbreviations” as well. **Phrases** such as “TNX FER CALL” come with
  word gaps and are typed without spaces; the time window has two parts
  (start within 2 s, then 0.6 s per character). **mixed** brings a phrase
  in roughly every third sequence; daily practice mixes this way from
  lesson 35. If your characters are not enough, the announcement says so
  at the start. With large text the choice buttons wrap.
- **Band levels fair with a low pitch:** without a narrow filter a very
  low tone is quieter. The level buttons then set the noise weaker by
  that amount, and it counts accordingly for QRN-proof.
- **Focus returns:** after questions, settings, the band window and help,
  the focus is back where it was. Escape in a question no longer goes to
  the main window, and Tab reaches “Yes” before “No”.
- **Announcements:** F5 (stop and start again right away) during an
  announcement no longer starts a double run, nor does the start button
  during a daily practice block announcement. In the band window the
  noise slider is announced as “signal to noise”; values of
  switched-off interference are dimmed.
- **Small things:** help has the button “Open online in browser” (without
  a browser the address is shown). Screen reader detection no longer
  trips over unusual process names and also works in the AppImage.
- **Manual:** new section “Your learning path” with nine steps from the
  first characters to band conditions; NVDA sleep mode and JAWS added.

## 2.49

- **Messages and questions are announced:** questions such as “Next Koch
  lesson?” are read out, including “Enter: yes. Escape: no.” The space bar
  no longer says yes by accident; F9 and F11 work there too.
- **Daily practice waits for its announcement:** each block is announced
  (“Daily practice, Warm-up: Characters, 3 minutes”), and only then comes
  the first character. Until now the announcement ran over the Morse tone,
  and the first character counted as too slow. The new character of a
  lesson also plays only after the announcement.
- **Backing up and restoring data without errors:** on Linux the file
  dialog failed with “Unexpected error” while announcements were on. The
  file dialog is now preceded by what comes and what Enter and Escape do;
  meanwhile the mouse pointer shows the wait, and a second press does not
  open a second dialog. Restoring is not possible while an exercise is
  running, even if it was started during the announcement.
- **CW QRM follows the pitch:** if you change the pitch, the neighbour
  keeps the chosen distance; “Zero beat” stays on your own frequency.
- **First start no longer silent:** on the very first start the program
  says that F9 turns on spoken feedback and F11 tells you where you are.
  If a screen reader is running, announcements are on right away.
- **Scroll areas follow the keyboard:** if you tab to a field that is out
  of sight with large text (for example in Band conditions or Statistics),
  the area now scrolls along.
- **Help to listen to:** when it opens, the help says where it is; arrow
  down and up read paragraph by paragraph, and a search hit reads its line.
  New is the “Open in browser” button.
- **F9 and F11 in every window:** in Settings, Band conditions, Help and
  the network windows too, F9 toggles announcements and F11 says which
  window and which control you are on.
- **Start errors are announced:** if an exercise does not start (for
  example without valid characters, without your own callsign in Contest
  or without a name in Network), the announcement gives the reason instead
  of only writing it to the status line.
- **Daily practice with orientation:** during a block F11 says which block
  is running, how far the practice is and which stars you have today. The
  hint “Press Esc again to end the daily practice” and other announcements
  are no longer cut off by the next character, and F11 right after
  “Wrong …” or “Too slow …” no longer by the correction tone.
- **Drop-down lists to listen to:** in an open list (font size, language,
  mode …) the announcement reads the entry while you move, e.g. “English,
  2 of 2”.
- **Band conditions with feedback:** the level buttons are called “Level
  light” and so on and confirm the choice; in that window F11 also says
  which level the settings match. The levels are now at the top, Tab
  starts there, and right below it says which level the settings match.
- **Better contrast in the light colour scheme:** input fields, slider
  handles and the focus frame stand out clearly; hints and greyed-out
  entries are easier to read.
- **Statistics without a mouse:** the awards table reads the condition of
  each row, the preview is announced. The lifeline can be reached with
  Tab; the arrow keys go through the days and announce their values. In
  the Statistics tab F11 also gives progress and lifeline.
- **Adjustable voice:** under “Settings …” you can choose the speaking
  rate (70–200 %) and the announcement volume (25–100 %).
- **Smaller improvements to announcements:** “Ctrl+,” is spoken with
  “comma”, “20/10 WPM”, “3 / 10” and “S/N +8 dB” in an understandable way.
  The status line says “Ready. Start with F5.” (in Contest “Start with
  F10.”); More options open/closed, the hint on slow character speed,
  “takes effect after restarting” and the download progress of an update
  are announced. After the evening summary and an award the focus
  returns. Slightly stronger accent and station colours, clearer focus on
  the blue start button.
- **Cleaner signals:** dots and dashes now have exactly their length
  between the half-amplitude points (at high speed dots sounded up to a
  quarter too short); the speed stays the same. Changing or switching on
  noise or interference in the middle of a tone no longer clicks, the
  levels glide over. AGC pumping starts exactly at the crash. The signal
  to noise ratio is now given “in the receiver filter (300–2700 Hz)”, in
  the ear about 16 instead of 17 dB more.
- **Steeper CW filter and more realistic QRN:** the 500 Hz filter now
  clearly removes QRM “far” (300 Hz off −13 instead of −7 dB) but rings a
  little more. Crashes and thunderstorms crackle as a series of short
  single discharges instead of smooth noise bursts.
- **Fading and receiver as on the band:** QSB and flutter fading now vary
  randomly (Rice fading): mostly shallow, now and then a deeper dip, from
  “heavy” occasionally very deep ones. The receiver turns up the gain in
  the gaps, so between characters the noise gets louder; during the tone
  the set signal to noise ratio applies. This makes “light” and “medium”
  a little harder.
- **Low tones and sidetone:** at pitches below 400 Hz the receiver filter
  now attenuates the signal too (−3 dB at 300 Hz); a low tone used to be a
  little easier. The same level is then harder; the band window and the
  manual point this out, with the 500 or 250 Hz CW filter it does not
  apply. Your own sidetone (Contest) is 3 dB quieter and, together with
  the band noise, limited less often.
- **Installing from source:** now requires piper-tts 1.5 or later; with
  1.3 and 1.4 the program quit at the first announcement. The manual says
  that the setup has to be repeated in the new folder when updating.

## 2.48

- **No more crash when closing during an announcement:** closing the
  window while speech output was still being generated crashed the
  program (on Linux with a crash report). Now it waits briefly until the
  announcement is done. A running MP3 export is cancelled and the
  half-written file deleted.

## 2.47

- **Help with F1:** F1 opens the manual at the section of the tab you are
  in. In Contest F1 still sends CQ; there the “Help (F1)” button opens the
  help. On the Mac Cmd+Shift+H works too.
- **Help in the Network tab:** the help button jumped to the wrong section
  there; it now opens the chapter on the network.
- **Manual revised:** missing options are described (duration, feedback
  beep, time limit, group length, switches in the Speak tab), technical
  terms are explained, and there is a hint in case the AppImage does not
  start because of FUSE.

## 2.46

- **Review box at a glance:** the Statistics tab shows which characters are
  in each box, from “Box 1 · every day” to “Box 6 · every 32 days”. F11
  reads it out too.

## 2.45

- **More room during a run:** for groups, words, callsigns and in
  Non-stop the options are hidden during a run, so the answer field,
  feedback and Stop stay visible without scrolling even with a large font
  or a small screen.
- **No accidental end of the daily practice:** Esc or F5 only end it on the
  second press within three seconds; the first is shown and announced.
  There is also an “End daily practice (Esc)” button.
- **Esc stops everywhere:** in all practice tabs, also from the answer
  field (in the contest Esc still aborts sending). F5 in the contest
  before the start reminds you that F10 starts.
- **Shortcuts on the buttons:** “Start (F5)”, “▶ Daily practice (10 min,
  F12)”, “Settings … (Ctrl+,)”, “Listen (Ctrl+P)” and so on.
- **Goal and result visible:** in the Characters exercise “23 of 50
  characters, goal 90 %” is shown next to Start; after stopping, the
  result is in the status line.
- **Speed in CPM:** with Farnsworth the header shows the effective speed
  you hear (“≈ 50 CPM effective” at 20/10).
- **Help at the tab:** Help opens the manual at the section of the tab
  you are in.
- **Settings:** the daily goal is now in the “Settings …” window
  (“Practice” box). After changing language or contrast, “Restart now”
  restarts the program right away.
- **Large fonts and small screens:** the header and the daily practice bar
  wrap instead of overlapping; in the band conditions window Listen and
  Close stay at the bottom and get the focus on opening.
- **Small things:** legend for the week strip, the “Content” row is a
  single Tab stop, column headings no longer cut off.

## 2.44

- **Finest hours award:** the “Star collector” award is now called “Finest
  hours”; levels already reached are kept. Stars and practice days dated
  after today (clock set wrong) no longer count for Finest hours and
  Endurance.
- **Faster start with announcements:** the window appears before the voice
  is loaded (about 0.5 instead of 1.3 seconds); the first announcement comes
  a moment later instead.
- **Faster awards:** after a run the awards are evaluated once instead of
  three times, and a small digest is stored for each run. Start and
  evaluation stay quick and need less memory even after years of practice.
  The first start after the update creates the digests.
- **More robust:** a brief database read error can no longer drop runs from
  the awards for good. With a second program window open, the evaluation no
  longer waits up to 5 seconds. A speech output error no longer stops the
  practice flow.

## 2.43

- **New award Star collector:** all daily practice stars together, bronze
  from 50, silver from 200, gold from 500, platinum from 1,000 stars. Every
  star counts, also from weeks without the weekly goal reached.
- **Where am I? (F11):** now also reads out the remaining time and the
  current score in Non-stop and Contest (“time left 3 minutes 12 seconds”,
  “rate 80 per hour”).
- **Update in English:** with the English interface, the update window
  will show what is new in English.

## 2.42

- **Update:** a window of its own shows what is new in the new version;
  the announcement reads out the headings (F11 repeats). After “Update
  now” the progress is shown in the window, after an error the reason and
  the download link. After “Later” the button “Update …” in the footer
  brings the window back at any time; by itself the Morsetrainer asks
  again for this version after seven days.
- **Speak in English:** with the English interface the tab uses the
  English voice, spells with the English alphabet (Charlie, Mike, X-ray)
  and says the English meaning.
- **Prosigns** are announced by name instead of spelled: “=” separator,
  “+” end of message, <SK> end of contact, <KN> over to you only, <BK>
  break (German Trennung, Spruchende, Ende der Verbindung, bitte kommen,
  Unterbrechung). Also in notes such as “New character: <SK> · key *”
  (“… key asterisk”).
- **Progress** (Statistics tab) gives the period (“19 sessions on
  2026-09-30” or “from … to … on 6 days”) instead of “since”; sessions
  with fewer than 5 characters (short tries) no longer count there.

## 2.41

- **Non-stop and Speak:** the content is chosen with option buttons
  instead of a drop-down list, as in the One by one tab, at the top of the
  tab; all choices at a
  glance, the arrow keys switch, the announcement says “Content …”. Locked
  during a run.
- **Announcements:** for 1 it says “one minute”, “one second”, “one failed
  attempt” and “one character” instead of “1 minute” etc. Messages why a
  run does not start (e.g. too few characters for phrases in lesson 1,
  invalid input) or stops (no sound output) are now spoken as well as
  shown.
- **Searching the help:** also finds what is written differently: umlaut
  spelling and hyphens do not matter, other words for the same thing
  (“shortcut” finds “shortcuts”, “keyboard” finds the keyboard section) and
  parts of compound words; this is said along with the result. If it is
  only in the other tab (manual or changes), the search says how often.
- **Speak:** always spells in the phonetic alphabet (Alfa, Bravo …); the
  choice “German letter names (A, Be, Ce)” is gone.
- **Manual** restructured: getting started, one section per tab, keyboard
  shortcuts as a table, numbered chapters with a table of contents.
- **One by one:** F5 now starts and stops Characters, Groups, Words and
  Callsigns too, as in the other tabs.

## 2.40

- **New tabs:** Characters, Groups, Words and Callsigns now share the
  **One by one** tab (choose under “Content” at the top, as in the other
  tabs; the choice is saved): one at a time, with an answer. “Continuous” is now **Non-stop**:
  copy continuously without pauses. Ten tabs become seven; Alt+1 … Alt+7
  select them (1 One by one, 2 Non-stop, 3 Speak, 4 QSO, 5 Contest,
  6 Network, 7 Statistics), Alt+0 still goes to Statistics, and Alt+8 or
  Alt+9 announces that there are only seven. In the One by one tab,
  pressing Alt+1 again moves on to the next content, the arrow keys work in
  the “Content” row, and the announcement names the content (“Tab One by
  one, Groups”, “Content Words, option button”). Settings, statistics and
  history are kept.
- **Band in the answer pause:** in Groups, Words and Callsigns the band
  keeps running 6 dB quieter after each sequence instead of falling
  silent; it comes back up with the next sequence (smooth crossfade).
  It can be switched off with “Band in the answer pause” in the band
  conditions window (counts the same for level and award). The solution
  after too many failed attempts now comes without interference.
- **New interference** under “More interference”: switching power supply
  (buzz with a wandering whistle), PLC (powerline data noise), electric
  fence (a tick about every second) and key clicks (the neighbouring run
  keys hard; the clicks get through even a narrow filter). On the network,
  participants from 2.40 on hear the new interference too, older versions
  do not. “All on” now only switches on the interference in the upper
  card, not the collapsed extra ones. With announcements (F9) the band
  fades out before the feedback so it is easy to understand.
- **Keyboard:** Enter presses a focused button, like the space bar (e.g.
  “Close” after tabbing through).
- **Announcements:** “Hz”, “kHz”, “min” and “s” (after a number) are
  spoken as “hertz”, “kilohertz”, “minutes” and “seconds” instead of being
  spelled out; the German voice pronounces “Fading”, “Pile-up” and the
  contest types (CQ WW, WPX, WAG, ARRL DX, IARU HF) the way hams say them,
  abbreviations spelled like callsigns (also with the English voice). In
  the statistics single characters such as “?” are named, confusions read
  as “B 9 times” or “once”, and headings such as “Ø reaction (s)” as
  “average reaction in seconds”. Brackets are no longer read out
  but become a pause; “state/power” is read as “state or power”.
  Number fields say their unit (“Show solution after, 3 failed attempts”,
  “Duration, 5 minutes”).
- **Statistics:** “confused with” no longer lists “–” for a character
  that was not recognised at all; it only counts as wrong.
- **Network:** when the session opens, the trainer hears address and PIN
  (also with F11), the address number by number with “dot”, the PIN digit
  by digit.
- **Contest:** callsigns in the fields and in the log are announced in the
  phonetic alphabet (Delta, Lima, One …).
- **Closing a window:** the announcement says where you are now (“Back in
  the main window. Tab One by one, Groups.”).
- **Statistics:** the column “Ø time” is now “Ø reaction” and shows the
  time from the last dot or dash to your input (correct answers, measured
  values), the same in every exercise. Before, it was the time from the
  start of the character, so long characters and slow speeds looked worse.
  When copying along it counts from the end of the tone or from your
  previous key, whichever is later: writing behind or listening to the
  whole group first no longer counts as “recognised slowly” (also for the
  review box and the weighting). “Ø WPM” per character counts only correct
  answers, from the start of the character and at most as fast as it was
  sent; in Non-stop, QSO type-along and on the network it used to show
  absurdly high values (around 66 WPM at 20 sent).
- **One by one, Characters:** the answer counts from the end of the last
  dot or dash. Before, a very quick key in the gap after the character was
  dropped and then ran out as “too slow”; the time limit now also counts
  from the end of the tone, as described.
- **Tables** (awards, statistics, contest log): when you Tab into one, the
  first row is selected and the arrow keys work right away. When a window opens, the announcement says
  its name (“Window Band conditions”); if the window speaks itself, the
  name comes first. Typing in settings fields and number fields is
  announced (characters spelled out, deletions with “deleted”); the
  “Characters” field reads its content character by character.
- **Font size:** arrows of number fields and drop-down lists, scrollbars
  and sliders grow with it; the full result (Non-stop) and the solution
  (Network) start at the size set.
- **Narrow filter at a low pitch:** the filter moves with your pitch like
  an IF filter in a rig and removes the same amount of noise at every
  pitch. Before, at a low pitch it ran into the lower edge of the SSB
  filter and removed more noise than shown; this way the level and the
  QRN-proof award do not depend on the pitch you choose.
- **Mac:** the manual states the minimum version macOS 14 (Sonoma).
- If a voice is missing from the packaged program, the message now
  suggests downloading the program again instead of pointing to a script.
- **Listening without a time limit:** it runs until you stop it (button,
  Ctrl+P or closing the window).
- **Statistics:** below the table it says what “Ø reaction”, “Ø WPM” and
  “–” mean.
- **Contest:** stations from W8 (Ohio, Michigan) send CQ zone 4, from W9
  ITU zone 8; in the WAG some DL stations send “NM” (non-member) instead
  of a DOK.
- **Announcements:** the German voice says “Quebec” as prescribed
  (“Keh-beck”). Minimising a window (or switching workspaces) is no longer
  announced as “Back in the main window”.
- **Keyboard:** Ctrl+B, Ctrl+P and Ctrl+F also work with Caps Lock, on the
  Mac also Cmd+B.
- **Electric fence:** ticks at most once a second, as the standard for
  fence energisers requires.
- **Error messages:** if the Morsetrainer cannot open a window, it says so
  on the console (on Windows in a message box) and names the error log
  instead of vanishing silently. If there is no sound, the message says
  what to do (device busy, none found, unplugged). `--help` and
  `--version` show usage and version.
- **After the update** a note says once where Groups, Words and Callsigns
  are now.
- **Headphones changed:** if the audio device is gone (unplugged, none
  found), the trainer reads the devices again and tries once more instead
  of staying silent until a restart (especially on the Mac).
- **Settings** that cannot be saved on exit (e.g. in a read-only folder)
  are reported instead of being lost silently.
- **Band conditions:** the window advises practising at “light” to
  “medium”; “heavy” is for polishing.
- **Older Intel Macs:** the manual states Python 3.10 to 3.13 and macOS 13;
  with Python 3.14 the trainer can be set up there without speech instead
  of not at all. The development guide lists the Linux packages needed.
- Internal: minimum versions of the dependencies, voice download pinned to
  a fixed revision, release builds with fixed versions
  (packaging/constraints.txt), the build self-test also checks the sound
  and window libraries. Opening and closing the sound output are guarded
  against simultaneous access; stopping and restarting at once can no
  longer make the pause noise run twice. The tests also run with Python
  3.10, plus a trial installation on Windows and macOS. New picture in the
  README. More tests.

## 2.39

- **Listen in the band conditions window** (Ctrl+P): a 15-second CQ at
  your pitch and speed under the conditions set, without switching to a
  tab. Changes can be heard at once; it counts for nothing. Disabled
  during a run and on the network.
- **Announcements:** if a new announcement comes while another is still
  speaking, the run continues only after the new one. Until now the next
  Morse tone could cut it off (e.g. when switching tabs in the middle of
  an announcement).
- **Band conditions window with a scroll bar:** with a large font or a
  small screen it no longer fits completely; what is missing can now be
  reached.
- **Continuous:** the evaluation after stopping shows the last 90
  characters instead of 30 (in lines of 30), “Your input” the last 120;
  the number is in the heading.
- **Smaller font sizes too:** 90 % and 75 % for small screens.
- **Search the help** with Ctrl+F: Enter jumps to the next match,
  Shift+Enter to the previous one; all matches are highlighted.
- **Network: everyone hears the same QRM.** With CW QRM, each participant
  used to hear a different neighbouring QSO and different thunderstorms,
  carriers and crashes. Now it is all the same (trainer and participants
  from 2.39).
- Internal: the tests now run automatically on GitHub with every push, and
  a release is only built when they pass. Comments and descriptions in the
  source code have been revised (what the code does instead of version
  history).

## 2.38

- **Selectable CW filter:** 2.4 kHz (as before), 500 Hz or 250 Hz around
  your pitch. Signals, noise, QRM and SSB QRM pass through it, your own
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
- **Spoken announcements (accessibility, F9):** the
  program uses its built-in voice to announce results (spelled in Groups,
  Words and Callsigns, errors in Characters), the end of a run, tab
  changes and the daily practice cards; F11 reads out where you are. The
  program waits for the announcement. German or English voice to match
  the interface; without a voice, F9 and F11 play an error tone. Also in QSO (next
  step, quiz fields, result with the correct values), in Contest (logging
  errors right after the TU, in the audio), in the Statistics tab (F11
  reads an overview) and in tables (selected row). Controls reached with
  Tab announce their name, kind and state, keyboard changes too (a small
  built-in screen reader). On the network, participants hear connecting
  and disconnecting, the result of each answer and of the run; the
  trainer's sequences take priority. The daily practice's evening summary
  and the award window are read out in full; in the Speak tab start
  problems, the end and the MP3 export.
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
- Band conditions with radio terms: “band noise” instead of “noise”, “SSB
  QRM (detuned speech)” instead of “SSB babble”, “chirp (chirpy
  transmitter)”.
- **More interference** (expandable in the band window, not part of the
  levels): thunderstorm (QRN in bursts), AGC pumping after crashes,
  flutter (aurora), carrier (someone tuning up).
- **Mac:** Cmd+Q now saves settings such as language, font size and
  contrast; Cmd+Comma and “Settings …” in the app menu open the settings;
  Cmd+0 resets the font. Because F9, F11 and F12 are media keys there:
  Cmd+Shift+A (announcements), W (where am I), T (daily practice).
- **Running from source:** the manual now lists the step that downloads
  the voices (`packaging/get_voice.sh`); the script also runs with the
  bash shipped with macOS.
- The English voice makes the packages a good 60 MB larger; the Windows
  exe starts a little more slowly because of it.
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
