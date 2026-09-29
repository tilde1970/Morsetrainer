# Morsetrainer

A CW trainer for everyone from beginners to contesters, developed by **DL4YM**.

From learning single characters with the Koch method up to running your own
contest pile-up under realistic HF conditions.

**Language:** the program starts in German. Switch to English under
„▸ Weitere Optionen“ → „Sprache / Language“; it takes effect after a
restart.

## Training modes

| Tab | What you practise |
|---|---|
| **Characters** | Recognise single characters; after each answer you see your time and the current limit, e.g. “0.38 s, limit 1.20 s”. With time limit (Instant Character Recognition): the limit gets shorter while you answer reliably. After a confusion you hear the correct character and the one you typed back to back. |
| **Groups** | Copy groups of characters. The group length can grow: start short, one longer after 5 correct groups, one shorter after 2 wrong groups (each on the first attempt). |
| **Words** | CW abbreviations, Q codes and QSO words, only from characters you already know. The default is “Listen first”: hear the whole word, then type; a slow answer is noted. R, K and the prosigns KN and SK also appear (but do not count as words for the minimum). A weak character comes up more often, but in changing words. The meaning is shown after the answer. You can add your own words (see Data). |
| **Callsigns** | Real callsigns from the Super Check Partial list, by default only from characters you have already learned (from Koch lesson 23 with the first digit). Occasionally with /P, /M, OE/… as in contests. Optionally as a **RufZ run** (modelled on RufzXP): 50 callsigns, one attempt each, the speed grows, score = length × effective speed, best score (with starting speed) and history; afterwards you can replay the missed and slowly recognised callsigns (F6): first just listen, then again with the solution, at the original speed. |
| **Continuous** | The audio keeps running without waiting, you type along (as when listening on the air); characters come in groups (default 5) with a word gap in between. Instead of random characters also as **plain text**: words, typical QSO phrases (“TNX FER CALL”, “UR RST 599”), callsigns or complete QSOs in one go (plain text does not count for the lesson). After stopping (F5 or Esc) a comparison shows the last characters. A key only counts if it fits the character: not guessed in advance and at most 5 s after it; typing too much counts as an error. |
| **Speak** | Listen & say without a keyboard (like Morse Code Ninja): Morse code, a thinking pause in which you say out loud what you heard, then a voice announces the solution – characters, groups and callsigns spelled (German letter names or phonetic alphabet), words and phrases as a whole or with their meaning – and the code comes once more. The thinking pause is deliberately short (default 1 s plus 0.3 s per character). Content: characters, groups, words, phrases, callsigns. **Save as MP3** for on the go (phone, car). Counts only for practice time. *The voice is German.* |
| **QSO** | Listen to complete QSOs: normal QSO or contest runs (CQ WW, CQ WPX, WAG, ARRL DX, IARU HF) with adjustable pile-ups (default off). Evaluation via log check, by typing along, as **head copy + questions** (no notes, afterwards content questions about name, QTH, rig, weather … or exchange) or listen only. Next to the length the estimated duration is shown; how often you used “Again” before checking is noted. |
| **Contest** | You are the running station (similar to Morse Runner): call CQ, pick up callers, send the exchange, log. As in a real contest, callers sometimes answer to an almost correct call – if you notice the mistake, correct the call and confirm with Enter (“Call TU”), otherwise “Busted” appears in the log. “?” in the call field asks back (DL1?, DL?ABC). Speed and pitch spread of the callers are adjustable, at the end there is a summary by type of error; F10 starts and ends. |
| **Network** | Practise as a group on the local network (class, club evening): a trainer sets the pace, everyone hears the same sequence on their own headphones and copies it; the trainer sees live who typed what. See below. |
| **Statistics** | Overall statistics per character, **spaced repetition** (review over days: characters recognised reliably and quickly come back after 1, 2, 4 … 32 days, uncertain ones the next day; decided once a day from 5 attempts, promoted only from random characters; due ones come up more often with “weak favoured” and can be practised specifically), most frequent confusions (with a button to practise them), daily goal and progress history per mode. |

In **Groups, Words and Callsigns** you can choose:

- **Input:** *Copy while listening* (type while the audio plays), *Listen
  first* (type after the audio) or *Head copy* (type nothing; Enter reveals,
  then J = knew it, N = didn't). Head copy relies on your own assessment and
  therefore does not count for the overall statistics and the lesson.
- **Speed adapts** (as in RufzXP): correct on the first attempt +1 WPM,
  wrong on the first attempt −1 WPM – meaning the effective speed. With
  Farnsworth the gaps get shorter first; once they are gone, the character
  speed increases. The characters get slower only down to 15 WPM, below that
  the gaps get longer, so you cannot count dits and dahs. The same rule
  applies to “Adjust speed automatically” in the QSO tab. The progress
  history shows the effective speed (e.g. 10 at 20/10 WPM).
- **Band conditions** in three levels: light, medium, heavy.

### Learning path for beginners

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
   single characters. After an error only the wrong positions are marked
   and the group comes again – listen to it instead of reading it. After 3
   failed attempts you see and hear the solution.
4. If you get 90 % on the first attempt in a session of at least 50
   characters in groups (or in Continuous mode), the next lesson is
   offered. A first attempt only counts for the lesson if you did not repeat
   the group with the space bar and answered quickly (1.5 s plus 0.6 s per
   character after the end of the tone); typing too much counts as an
   error. Weak and new characters automatically come up more often. After
   the 40 lessons of lcwo.net, lessons 41–44 add the prosigns from QSOs:
   AR (key `+`), KN (`(`), SK (`*`) and BK (`#`).
5. From lesson 6 there are enough words for the **Words** tab (words with
   the newest character are favoured), then **Continuous** and **QSO**.
6. In the **Statistics** tab (confusions of the last 30 days), “Practise the
   4 most frequent” shows which characters you confuse and practises exactly
   those against each other. “↩ Lesson” at the top takes you back to your
   lesson.

Also helpful:

- **Short and daily** beats long and rare: the footer shows today's
  practice time, the daily goal (adjustable in the Statistics tab) and how
  many days in a row you have reached it.
- **Vary pitch and speed slightly** (shared setting): if you only ever hear
  exactly one sound, you will find it harder on the band.

### Band conditions (QSO and Contest)

Each can be switched on and adjusted: noise, static crashes (QRN), QSB,
chirp, SSB babble and CW QRM on the adjacent frequency.

### Network: practising as a group

For classes and club evenings: all computers are on the same network
(Wi-Fi or LAN), one is the trainer, the others join as participants. Only
text is sent; each computer generates the sound itself – no dropouts,
with its own headphones and its own pitch.

**Trainer:** in the *Network* tab choose “Trainer”, **Open session**. The
address and a four-digit PIN for the participants are shown. Then choose
content (characters, groups, words, callsigns, phrases, QSO plain text
or **own text**, one line per sequence; prosigns as + for AR, ( for KN,
* for SK, # for BK), number of sequences, answer time and band conditions; character
set, speed and Farnsworth come from the header. At a slow character speed
(below 18 WPM) the tab points out that the characters can be counted and
offers Koch speed 20/10. After **Start** everyone gets
the same sequence at the same time. The next one comes once everyone has
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
↻ = repeated for everyone) with what was typed and the time to Enter.

**Participant:** choose “Participant”, enter name or callsign and the PIN,
**Search** (or enter the trainer's address) and **Connect**. You type
while the tone is still running, Enter confirms; there is one attempt per
sequence, then the solution is shown. If it was not fluently correct,
the sequence is played again with the solution (the trainer can switch
this off). If you are not finished in time, what you have typed so far is
scored. The results count for your own statistics like a normal run,
with the time per character as when copying along; after “Repeat for
everyone” or when too slow, a correct character counts as uncertain and
comes up more often with “weak favoured”. Practice time only counts while
a run is going, not while waiting for the trainer.

The trainer needs port 7373 (TCP) and 7374 (UDP) for the search. On
Windows the firewall asks the first time – allow it for private networks.
If the search finds nothing (some Wi-Fi networks block broadcasts), enter
the address shown by hand.

### Help in the program

The **Help** button on the right of the footer shows the changes of the
versions (CHANGELOG) and this manual.

### Keyboard shortcuts

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

## Running from source

Requires Python 3.10 or newer with Tk.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
packaging/get_voice.sh           # voice for the Speak tab (about 63 MB)
python main.py
```

Tests:

```bash
python -m unittest discover tests
```

## Project structure

```
main.py              start file
morsetrainer/
  app.py             main window with all tabs
  i18n.py            language (German/English), texts in i18n_en.py
  core/              Morse code, audio, band conditions, texts, statistics
  modes/             one module per training tab
  net/               network mode (trainer, participants, scoring)
  widgets/           reusable interface building blocks
tests/               automated tests
packaging/           AppImage build (icon, desktop file)
.github/workflows/   builds AppImage and exe for releases
```

## Data

When started from source, the data lives in the program directory; for the
AppImage in `~/.local/share/morsetrainer/`, for the exe in
`%APPDATA%\Morsetrainer\`.

- `stats/`: session logs, overall statistics (`all_time.json`), review box
  (`review.json`), results of QSO checks and contests (`results.jsonl`) and
  practice time per day (`practice.json`); also the CSV tables from the
  Network tab (`…-netzwerk.csv`).
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

## License

MIT, see [LICENSE](LICENSE). © 2026 DL4YM

---

73 de DL4YM
