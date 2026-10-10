# Morsetrainer

A Morse code (CW) trainer for Windows, Linux and macOS, for everyone from
complete beginners to contesters, developed by **DL4YM**.

From learning single characters with the Koch method up to running your own
contest pile-up under realistic HF conditions – alone at your own computer
or together at a club evening on the local network.

**Language:** the program starts in German. Switch to English with
Ctrl+Comma (or the “Einstellungen …” button at the top right) → “Sprache /
Language”; it takes effect after a restart. The screenshots show the German
interface. German overview: [README.md](README.md).

## What it does

- **Koch method** with the lessons of lcwo.net and Koch speed 20/10: hear
  characters as a sound pattern instead of counting dits and dahs. The
  next lesson is offered once you get 90 %.
- **Daily practice (10 min):** puts together what is due today – warm-up,
  main part, cool-down – with three stars a day and a weekly goal.
- **Exercises:** single characters with time limit, groups, words and Q
  codes, real callsigns (also as a RufZ run), continuous copying, listen &
  say without a keyboard (also as MP3), complete QSOs and contest operation
  as the running station, as in Morse Runner.
- **Band conditions:** noise, QRN, QSB, chirp, SSB babble and CW QRM, each
  adjustable.
- **Statistics:** per character, spaced repetition over days, most frequent
  confusions to practise specifically, printable awards in bronze, silver
  and gold, lifeline.
- **Network:** class or club evening on the local network. The trainer
  sets the pace, everyone hears the same sequence and types along, the
  trainer sees live who typed what. Also with a fixed pace for pencil and
  paper.
- **Accessible:** the trainer aims to be usable without looking at the
  screen. A built-in voice announces results, tabs, windows and controls,
  everything works from the keyboard, plus font size up to 200 % and high
  contrast.

## Screenshots

### Copying at Koch speed

<img src="docs/bilder/gruppen.png" width="640" alt="Main window (German interface) in the One by one tab with the content Groups. At the top Koch lesson 15, 20 WPM, 600 Hz and Farnsworth 10, below the exercise options, the answer field with ESJ and the feedback “Richtig: ESJ” (correct).">

### Award to print

<img src="docs/bilder/diplom.en.png" width="640" alt="Sample Koch award in gold for DL1ABC, Max Mustermann, in the style of a certificate: a straight key on the left, a club house with an antenna mast on the right, a gold seal at the bottom and the award number at the top right.">

### Club evening on the network

<img src="docs/bilder/netzwerk.png" width="640" alt="The trainer's table at a club evening (German interface) with four participants: for each name the status, the current answer, the share of correct characters, the fluently correct sequences and the time. Below, the group result, 97 % of characters correct and 85 % of sequences fluent, the most common errors and the speed recommendation.">

## Download

Ready-to-run programs are on the
[Releases](https://github.com/tilde1970/Morsetrainer/releases) page; no
Python installation is needed:

- **Linux:** download `Morsetrainer-x86_64.AppImage`, make it executable
  (`chmod +x Morsetrainer-x86_64.AppImage`) and run it.
- **Windows:** download and run `Morsetrainer.exe`. The file is not signed,
  so Windows SmartScreen warns on first start (“More info” → “Run anyway”).
- **macOS (Apple silicon):** download `Morsetrainer-macOS.zip`, unpack it
  and drag `Morsetrainer.app` into Applications. The app is not signed, so
  you have to approve it on first start. How to do that, and what applies to
  Intel Macs, is in the [manual, section macOS](docs/Anleitung.en.md#macos).

`SHA256SUMS.txt` with the checksums sits next to the programs. To verify, on Linux run `sha256sum -c --ignore-missing
SHA256SUMS.txt`; on Windows run `Get-FileHash Morsetrainer.exe` in
PowerShell and compare with the line in `SHA256SUMS.txt`.

## First steps

1. Set **Koch lesson 1** at the top (K and M); “▶ listen” plays the new
   character.
2. Get to know the characters in the **One by one** tab under
   **Characters**, then copy under **Groups** while the audio plays.
3. Or simply press **▶ Daily practice (10 min)** (F12) – it switches the
   tabs by itself.
4. Press Ctrl+Comma (or the “Settings …” button at the top right) and
   enter your callsign and name; they appear on the awards.

Everything else is in the [manual](docs/Anleitung.en.md). In the program,
the **Help** button at the bottom right opens it, right at the section of
the tab you are in.

## Accessibility

The Morsetrainer aims to work well for visually impaired and blind users,
and this is being improved continuously:

- **Announcements (F9)** with a built-in voice, no screen reader needed:
  the result of each answer, the end of a run, tabs, windows, and fields
  and switches as you move through them with Tab. **F11** tells you where
  you are.
- **Keyboard:** everything is reachable without a mouse, with shortcuts
  for the main tasks (daily practice F12, band conditions, tabs).
- **Seeing:** font size with Ctrl+Plus and Ctrl+Minus (75–200 %), high contrast
  (black, white, yellow, at least 7:1); right and wrong are always shown as
  text too, not only as a colour.

Screen readers can hardly reach the interface (Tk) so far, which is why
the program speaks for itself. Details are in the
[manual, section 8 “Accessibility”](docs/Anleitung.en.md#8-accessibility).
Feedback on what is still missing or gets in the way is very welcome (see
“Feedback” below).

## Security

- **Updates:** on start the Morsetrainer asks when there is a newer
  release and, if you agree, replaces the exe or AppImage. Downloads come
  only from this repository over HTTPS, and the file has to match the
  checksum in `SHA256SUMS.txt`. This catches damaged downloads but is no
  substitute for a signature: whoever can replace the release can replace
  the checksum too.
- **Network mode:** unencrypted over TCP. Meant for a club or home
  network, not for public Wi-Fi. After 5 wrong PINs a computer is locked
  for a minute, and the trainer can remove strangers. The trainer does not
  pass on updates, it only tells its version number.

## More

- [Manual](docs/Anleitung.en.md): all tabs, daily practice, awards,
  network, keyboard shortcuts, data and backup
- [Changes](CHANGELOG.en.md) per version
- [Development](docs/Entwicklung.en.md): running from source, tests,
  project structure, release

## Feedback

Please report bugs, wishes and questions as an
[issue on GitHub](https://github.com/tilde1970/Morsetrainer/issues).
After a program error the Morsetrainer shows where the file `fehler.log`
is; please attach it to the issue.

## License

MIT, see [LICENSE](LICENSE). © 2026 DL4YM

---

73 de DL4YM
