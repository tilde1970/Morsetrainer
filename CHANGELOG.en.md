# Changes

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
